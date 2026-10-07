#include "ui.h"

#include <cfloat>
#include <cstring>
#include <mutex>
#include <string>
#include <vector>

#include "command.h"
#include "features.h"
#include "game.h"
#include "imgui.h"
#include "overlay.h"
#include "regions.h"
#include "runner_win.h"
#include "settings.h"

namespace {

typedef std::lock_guard<std::recursive_mutex> Lock;

const char *const DIPLOMACY_TAB = "외교·영토";   // features.cpp 의 탭 이름과 같아야 한다

Settings g_settings;
bool g_visible, g_capturing;
float g_rect[4];              // 창의 왼쪽 · 위 · 오른쪽 · 아래 (지난 프레임)
std::string g_confirm;        // 한 번 더 누르기를 기다리는 기능의 id
std::string g_notice;
int g_picked;                 // "외교·영토" 탭에서 고른 나라의 번호(없으면 0)
char g_filter[64];            // 나라 검색란
std::vector<int> g_regions;   // 이번 게임에 있는 지역
double g_regions_at = -10.0;  // 그것을 읽은 때(ImGui 의 시계, 초)
bool g_reporting;             // 테스트가 그린 것의 목록을 청했다(ui_report). 그 전에는 모으지 않는다
std::string g_report, g_drawing;   // 지난 프레임의 목록 / 지금 모으는 것

// 방금 그린 항목을 적는다: "이름\t가운데 x\t가운데 y\t보이는가(0/1)\t글". 테스트가 단추의 자리와 글을 여기서 읽는다.
void note(const std::string &name, const std::string &text)
{
    if (!g_reporting)
        return;
    const ImVec2 a = ImGui::GetItemRectMin(), b = ImGui::GetItemRectMax();
    g_drawing += name + '\t' + std::to_string(static_cast<int>((a.x + b.x) / 2)) + '\t' + std::to_string(static_cast<int>((a.y + b.y) / 2))
        + '\t' + (ImGui::IsItemVisible() ? "1" : "0") + '\t' + text + '\n';
}

void row(const Feature &f, const GameState &game)
{
    ImGui::PushID(f.id);
    long long value = 0;
    if (f.has_value) {
        long long &stored = g_settings.values[f.id];
        ImGui::SetNextItemWidth(150.0f);
        if (ImGui::InputScalar("##value", ImGuiDataType_S64, &stored)) {
            stored = stored < f.min ? f.min : stored > f.max ? f.max : stored;
            save_settings(g_settings);
        }
        value = stored;
        ImGui::SameLine();
    }
    const int region = f.target == Target::Player ? game.player : f.target == Target::Picked ? g_picked : 0;
    const bool missing = f.target != Target::None && region <= 0;   // 플레이어를 모르거나 나라를 고르지 않았다
    const bool asking = f.confirm && g_confirm == f.id;
    const std::string label = asking ? "한 번 더 누르면 실행합니다" : f.label;
    ImGui::BeginDisabled(missing);
    const bool pressed = ImGui::Button((label + "###run").c_str());
    note(std::string("run:") + f.id, label);
    if (pressed) {
        if (f.confirm && !asking) {
            g_confirm = f.id;
        } else {
            g_confirm.clear();
            g_notice = runner_enqueue(build_command(f, value, region)) ? "" : "대기 중인 명령이 많아 받지 못했습니다.";
        }
    }
    ImGui::EndDisabled();
    ImGui::TextDisabled("%s", f.help);
    ImGui::Spacing();
    ImGui::PopID();
}

// 나라 고르기: 이번 게임에 있는 나라를 이름순으로. 검색은 이름(한글 · 영문)이나 번호의 일부.
void picker(const GameState &game)
{
    if (ImGui::GetTime() - g_regions_at > 1.0) {   // 지역 수백 개를 읽는다 — 프레임마다 하지 않는다
        g_regions = game_regions();
        g_regions_at = ImGui::GetTime();
    }
    const RegionView view = region_view(g_regions, game.player, g_picked, g_filter);
    if (view.picked != g_picked) {                 // 다른 판을 불러와 그 나라가 없어졌거나, 그 나라로 플레이하게 됐다
        g_picked = view.picked;
        g_confirm.clear();
    }
    const std::string chosen = g_picked != 0 ? "고른 나라: " + region_label(g_picked) + " (" + std::to_string(g_picked) + ")"
                                             : std::string("고른 나라: 없음 — 아래 목록에서 고르십시오");
    if (g_picked != 0)
        ImGui::TextUnformatted(chosen.c_str());
    else
        ImGui::TextDisabled("%s", chosen.c_str());
    note("picked", chosen);
    ImGui::SetNextItemWidth(220.0f);
    ImGui::InputTextWithHint("##search", "검색 (이름 · 번호)", g_filter, sizeof(g_filter));
    note("search", g_filter);
    if (ImGui::BeginListBox("##regions", ImVec2(-FLT_MIN, 6.5f * ImGui::GetTextLineHeightWithSpacing()))) {
        for (int number : view.rows) {
            const std::string label = region_label(number) + " (" + std::to_string(number) + ")";
            const bool chose = ImGui::Selectable(label.c_str(), number == g_picked);
            note("row:" + std::to_string(number), label);
            if (chose) {
                g_picked = number;
                g_confirm.clear();   // 한 번 더 누르기를 기다리던 것은 다른 나라에 대한 것이었다
            }
        }
        ImGui::EndListBox();
    }
    ImGui::Spacing();
}

void settings_tab()
{
    ImGui::Text("창 여닫기: %s", hotkey_name(g_settings.hotkey_vk, g_settings.hotkey_mods).c_str());
    if (g_capturing)
        ImGui::TextUnformatted("새 조합을 누르십시오. ESC 는 취소입니다.");
    else if (ImGui::Button("단축키 바꾸기"))
        g_capturing = true;
    ImGui::Spacing();
    ImGui::TextDisabled("설정은 %%APPDATA%%\\SR2030ToyBox 에 저장됩니다.");
}

// 상태 줄: ToyBox 가 게임을 어떻게 보고 있는지 한 줄로.
void status_line(const GameState &game)
{
    const std::string text = !game.known ? "게임 상태를 읽을 수 없습니다 — 글쇠 방식으로 동작합니다"
        : game.multiplayer ? "멀티플레이에서는 동작하지 않습니다"
        : !game.in_game ? "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"
        : "플레이 중: " + region_label(game.player) + " (" + std::to_string(game.player) + ")";
    if (!game.known)
        ImGui::TextDisabled("%s", text.c_str());
    else
        ImGui::TextUnformatted(text.c_str());
    note("status", text);
}

}  // namespace

void ui_init()
{
    Lock lock(ui_mutex());
    g_settings = load_settings();
}

bool ui_visible()
{
    Lock lock(ui_mutex());
    return g_visible;
}

void ui_toggle()
{
    Lock lock(ui_mutex());
    g_visible = !g_visible;
    g_capturing = false;
    g_confirm.clear();
    g_report.clear();   // 닫힌 창의 목록을 남겨 두지 않는다
}

bool ui_is_hotkey(int vk, int mods)
{
    Lock lock(ui_mutex());
    return vk == g_settings.hotkey_vk && mods == g_settings.hotkey_mods;
}

bool ui_hit(int x, int y)
{
    Lock lock(ui_mutex());
    const float fx = static_cast<float>(x), fy = static_cast<float>(y);
    return g_visible && fx >= g_rect[0] && fx < g_rect[2] && fy >= g_rect[1] && fy < g_rect[3];
}

bool ui_capturing_hotkey()
{
    Lock lock(ui_mutex());
    return g_visible && g_capturing;
}

void ui_capture_key(int vk, int mods)
{
    Lock lock(ui_mutex());
    if (vk == 0x10 || vk == 0x11 || vk == 0x12)   // Shift · Ctrl · Alt 만 눌린 동안은 더 기다린다
        return;
    g_capturing = false;
    if (valid_hotkey(vk, mods)) {                 // ESC 만 누른 것은 valid_hotkey 가 거른다 = 취소
        g_settings.hotkey_vk = vk;
        g_settings.hotkey_mods = mods;
        save_settings(g_settings);
    }
}

void ui_draw()
{
    Lock lock(ui_mutex());
    g_drawing.clear();
    ImGui::SetNextWindowPos(ImVec2(40.0f, 60.0f), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(500.0f, 460.0f), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("SR2030 ToyBox", nullptr, ImGuiWindowFlags_NoCollapse)) {
        const GameState game = game_state();
        const bool faulted = runner_faulted();
        const bool blocked = faulted || (game.known && (!game.in_game || game.multiplayer));
        status_line(game);
        if (ImGui::BeginTabBar("tabs")) {
            const char *tab = nullptr;
            for (int i = 0; i < FEATURE_COUNT; i++) {
                if (tab != nullptr && strcmp(tab, FEATURES[i].tab) == 0)
                    continue;   // 이 탭은 앞에서 그렸다(같은 탭의 기능은 표에서 이어져 있다)
                tab = FEATURES[i].tab;
                const bool open = ImGui::BeginTabItem(tab);
                note(std::string("tab:") + tab, tab);
                if (open) {
                    const bool diplomacy = strcmp(tab, DIPLOMACY_TAB) == 0;
                    if (diplomacy && !game.known) {
                        ImGui::TextWrapped("게임 상태를 읽을 수 있을 때만 씁니다.");   // 이번 게임의 나라 목록을 모른다
                    } else {
                        ImGui::BeginDisabled(blocked);
                        if (diplomacy)
                            picker(game);
                        for (int j = i; j < FEATURE_COUNT && strcmp(FEATURES[j].tab, tab) == 0; j++)
                            row(FEATURES[j], game);
                        ImGui::EndDisabled();
                    }
                    ImGui::EndTabItem();
                }
            }
            if (ImGui::BeginTabItem("설정")) {
                settings_tab();
                ImGui::EndTabItem();
            }
            ImGui::EndTabBar();
        }
        ImGui::Separator();
        const int pending = runner_pending();
        const std::string last = runner_last();
        if (pending > 0)
            ImGui::Text("넣는 중: %s (남은 것 %d)", last.c_str(), pending);
        else if (!last.empty())
            ImGui::Text("마지막으로 넣은 것: %s", last.c_str());
        if (!g_notice.empty()) {
            ImGui::TextUnformatted(g_notice.c_str());
            note("notice", g_notice);
        }
        const std::string trouble = runner_notice();
        if (faulted)
            ImGui::TextColored(ImVec4(1.0f, 0.4f, 0.4f, 1.0f), "%s", trouble.c_str());
        else if (!trouble.empty())
            ImGui::TextUnformatted(trouble.c_str());
        if (faulted || !trouble.empty())
            note(faulted ? "fault" : "trouble", trouble);
        if (game.known && runner_direct())   // 직접 실행에서는 게임의 설정 창이 뜨지 않는다. 대신 열려 있던 패널이 스스로 다시 그려지지 않는다 [확인: 게임]
            ImGui::TextWrapped("일시 정지 중에는 게임 화면의 숫자가 그 패널을 누르거나 다시 열 때 바뀝니다.");
        else
            ImGui::TextWrapped("단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.");
        if (!game.known)   // 게임을 읽을 수 있으면 게임 밖에서는 단추가 꺼져 있으므로 이 주의가 필요 없다
            ImGui::TextWrapped("게임을 진행하는 중에만 누르십시오. 메뉴나 로비에서는 글자가 다른 곳에 들어갈 수 있습니다.");
    }
    const ImVec2 pos = ImGui::GetWindowPos(), size = ImGui::GetWindowSize();
    g_rect[0] = pos.x;
    g_rect[1] = pos.y;
    g_rect[2] = pos.x + size.x;
    g_rect[3] = pos.y + size.y;
    ImGui::End();
    g_report = g_drawing;
}

std::string ui_report()
{
    Lock lock(ui_mutex());
    g_reporting = true;
    return g_report;
}
