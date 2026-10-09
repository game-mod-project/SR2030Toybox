#include "ui.h"

#include <algorithm>
#include <cfloat>
#include <cstring>
#include <mutex>
#include <string>
#include <vector>

#include "command.h"
#include "features.h"
#include "game.h"
#include "imgui.h"
#include "keeper.h"
#include "log.h"
#include "overlay.h"
#include "products.h"
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
float g_footer;               // 바닥 줄들(알림 · 안내)의 높이 — 지난 프레임에 잰 것
Keep g_keep_sent;             // keeper 에 마지막으로 넘긴 최소 유지(저장한 설정과 같다)

// 방금 그린 항목을 적는다: "이름\t가운데 x\t가운데 y\t보이는가(0/1)\t글". 테스트가 단추의 자리와 글을 여기서 읽는다.
void note(const std::string &name, const std::string &text)
{
    if (!g_reporting)
        return;
    const ImVec2 a = ImGui::GetItemRectMin(), b = ImGui::GetItemRectMax();
    const ImVec2 middle((a.x + b.x) / 2, (a.y + b.y) / 2);
    const bool seen = ImGui::IsRectVisible(ImVec2(middle.x - 1, middle.y - 1), ImVec2(middle.x + 1, middle.y + 1));   // 가운데가 가려지지 않았다
    g_drawing += name + '\t' + std::to_string(static_cast<int>(middle.x)) + '\t' + std::to_string(static_cast<int>(middle.y)) + '\t'
        + (seen ? "1" : "0") + '\t' + text + '\n';
}

// 긴 안내 글(흐린 글씨). 창이 좁으면 줄을 바꾼다 — 그냥 두면 창 밖으로 잘린다(이미 써 본 사용자의 창은 저장된 크기 그대로다).
// name 으로 그 글의 오른쪽 끝(x)을 적는다 — 창 안에 드는지 테스트가 본다.
void help(const char *name, const char *text)
{
    ImGui::PushTextWrapPos(0.0f);
    ImGui::TextDisabled("%s", text);
    ImGui::PopTextWrapPos();
    note(name, std::to_string(static_cast<int>(ImGui::GetItemRectMax().x)));
}

// 되돌릴 수 없는 단추가 둘째 누름을 기다릴 때의 글: 무엇을 어느 나라에 하는지를 그 단추에 적는다.
std::string asking_label(const Feature &f, int region)
{
    std::string what = f.label;
    if (f.target != Target::None && region > 0)
        what += ": " + region_label(region) + " (" + std::to_string(region) + ")";
    return what + " — 한 번 더 누르면 실행합니다";
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
    const std::string label = asking ? asking_label(f, region) : f.label;
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

// 이번 게임에 있는 나라의 목록과 지금 고른 나라. "고른 나라" 줄을 그린다 — 탭의 구르는 내용 밖에.
RegionView choose(const GameState &game)
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
    return view;
}

// 나라 고르기: 이번 게임에 있는 나라를 이름순으로. 검색은 이름(한글 · 영문)이나 번호의 일부.
void picker(const RegionView &view)
{
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

// 설정의 최소 유지를 keeper 가 쓰는 꼴로: 국고는 백만 달러 → 달러.
Keep keep_of(const Settings &s)
{
    Keep keep;
    keep.treasury = s.keep_treasury;
    keep.treasury_floor = static_cast<double>(s.keep_treasury_value) * 1e6;
    for (int slot = 0; slot < STOCK_SLOTS; slot++) {
        keep.stock[slot] = s.keep_stock[slot];
        keep.stock_floor[slot] = static_cast<double>(s.keep_stock_value[slot]);
    }
    return keep;
}

// 창에서 고친 최소 유지를 keeper 에 넘긴다(save 면 설정 파일에도 적는다). 달라진 것이 없으면 아무것도 하지 않는다.
// 로그에는 켠 것 · 끈 것 · 켜진 채로 값이 바뀐 것을 적는다.
void send_keep(bool save)
{
    const Keep want = keep_of(g_settings);
    bool changed = want.treasury != g_keep_sent.treasury || want.treasury_floor != g_keep_sent.treasury_floor;
    if (want.treasury && (!g_keep_sent.treasury || want.treasury_floor != g_keep_sent.treasury_floor))
        log_line("유지 켬: 국고 %lld (백만 달러)", g_settings.keep_treasury_value);
    else if (!want.treasury && g_keep_sent.treasury)
        log_line("유지 끔: 국고");
    for (int slot = 0; slot < STOCK_SLOTS; slot++) {
        changed = changed || want.stock[slot] != g_keep_sent.stock[slot] || want.stock_floor[slot] != g_keep_sent.stock_floor[slot];
        if (want.stock[slot] && (!g_keep_sent.stock[slot] || want.stock_floor[slot] != g_keep_sent.stock_floor[slot]))
            log_line("유지 켬: %s %lld", product_label(slot).c_str(), g_settings.keep_stock_value[slot]);
        else if (!want.stock[slot] && g_keep_sent.stock[slot])
            log_line("유지 끔: %s", product_label(slot).c_str());
    }
    if (!changed)
        return;
    if (save)
        save_settings(g_settings);
    keeper_set_keep(want);
    g_keep_sent = want;
}

// 최소 유지의 수량 입력란. 치는 동안의 값(5, 50, 500 …)은 쓰이지 않는다 — ImGui 의 InputScalar 는 입력을 마쳤을 때
// (Enter, 다른 곳을 누름)에만 값을 넘겨준다. 치던 채로 창을 닫으면 친 것은 버려진다. 누르면 지금 값이 통째로 골라진다.
void keep_input(const char *id, long long *value, long long high, float width)
{
    ImGui::SetNextItemWidth(width);
    if (ImGui::InputScalar(id, ImGuiDataType_S64, value)) {
        *value = std::min(high, std::max(0LL, *value));
        send_keep(true);
    }
}

// 상태 줄의 뒤에 붙는 글: 최소 유지가 지금 무엇을 하고 있는가. 켜진 것이 없으면 빈 글.
// 까닭을 고르는 순서는 유지 검사(keeper_tick)가 쉬는 순서와 같다 — 값을 쓸 수 없으면 게임 밖에서도 "게임에 들어가면 적용"이라고 하지 않는다.
std::string keep_text(const GameState &game)
{
    if (keep_count(g_keep_sent) == 0)
        return std::string();
    if (!game.known)
        return keep_resting_text(g_keep_sent, "게임을 읽을 수 없어 쉽니다");
    if (!game_values_off().empty())
        return keep_resting_text(g_keep_sent, "값을 쓸 수 없어 쉽니다");
    if (game.multiplayer)
        return keep_resting_text(g_keep_sent, "멀티플레이에서는 쉽니다");
    if (!game.in_game)
        return keep_resting_text(g_keep_sent, "게임에 들어가면 적용");
    const GameValues now = game_values();
    return now.ok ? keep_active_text(g_keep_sent, now.used) : keep_resting_text(g_keep_sent, "값을 읽을 수 없어 쉽니다");
}

// 돈 탭의 단추 하나: 누르면 국고에 대한 요청을 대기열에 넣는다. 쓰는 것은 게임 창의 타이머에서다(keeper.h).
void money_button(const char *label, const char *name, Change change, double amount)
{
    const bool pressed = ImGui::Button(label);
    note(name, label);
    if (pressed)
        g_notice = keeper_enqueue({TREASURY, change, amount}) ? "" : "대기 중인 요청이 많아 받지 못했습니다.";
}

// 값을 쓰는 탭(돈 · 물자)의 머리. 쓸 수 없으면 까닭 한 줄만 그리고(name 으로 적는다) false — 내장 치트로 되돌아가지 않는다.
// 쓸 수 있으면 true 와 *now(탭이 보이는 동안 프레임마다 읽는다. 게임 밖이면 ok 가 거짓인 빈 값).
bool values_ready(const GameState &game, const char *name, GameValues *now)
{
    std::string off = game.known ? game_values_off() : std::string("게임 상태를 읽을 수 있을 때만 씁니다.");
    if (off.empty()) {
        *now = game.in_game ? game_values() : GameValues();
        if (game.in_game && !now->ok)   // 게임 안인데 값을 믿을 수 없다(재고 칸이 수가 아니다, 세계 자료를 읽지 못했다) — 까닭 없이 꺼 두지 않는다
            off = "게임의 값을 읽을 수 없어 쓸 수 없습니다.";
    }
    if (off.empty())
        return true;
    ImGui::TextWrapped("%s", off.c_str());
    note(name, off);
    return false;
}

// 돈 탭: 내장 치트를 거치지 않고 플레이어의 국고를 직접 고친다(기능 표가 아니라 여기서 그린다). 쓸 수 있으면 true.
bool money_tab(const GameState &game, bool blocked)
{
    GameValues now;
    if (!values_ready(game, "money:off", &now))
        return false;
    const std::string have = now.ok ? "국고: $ " + short_number(now.treasury) : std::string("국고: -");
    ImGui::TextUnformatted(have.c_str());
    note("money:now", have);
    ImGui::Spacing();

    ImGui::BeginDisabled(blocked || !now.ok);
    ImGui::SetNextItemWidth(150.0f);
    if (ImGui::InputScalar("##amount", ImGuiDataType_S64, &g_settings.money_amount)) {
        g_settings.money_amount = std::min(MONEY_AMOUNT_MAX, std::max(MONEY_AMOUNT_MIN, g_settings.money_amount));
        save_settings(g_settings);
    }
    note("money:amount", std::to_string(g_settings.money_amount));
    const double amount = static_cast<double>(g_settings.money_amount) * 1e6;
    ImGui::SameLine();
    ImGui::TextUnformatted("백만 달러");
    ImGui::SameLine();
    money_button("더하기", "money:add", Change::Add, amount);
    ImGui::SameLine();
    money_button("빼기", "money:sub", Change::Add, -amount);
    ImGui::SameLine();
    money_button("이 값으로", "money:set", Change::Set, amount);
    ImGui::TextDisabled("입력한 금액만큼 국고를 더하거나 빼거나, 국고를 그 금액으로 맞춘다");
    ImGui::Spacing();

    money_button("-$100 B", "money:-100b", Change::Add, -100e9);
    ImGui::SameLine();
    money_button("-$10 B", "money:-10b", Change::Add, -10e9);
    ImGui::SameLine();
    money_button("$0", "money:zero", Change::Set, 0.0);
    ImGui::SameLine();
    money_button("+$10 B", "money:+10b", Change::Add, 10e9);
    ImGui::SameLine();
    money_button("+$100 B", "money:+100b", Change::Add, 100e9);
    ImGui::TextDisabled("국고는 음수가 될 수 있다. 다른 나라의 국고는 건드리지 않는다");
    ImGui::EndDisabled();
    ImGui::Spacing();

    // 최소 유지는 설정이다 — 게임 밖에서도 켜고 끌 수 있다(쓰는 것은 게임 안에서만이다)
    if (ImGui::Checkbox("최소 유지", &g_settings.keep_treasury))
        send_keep(true);
    note("money:keep", g_settings.keep_treasury ? "1" : "0");
    ImGui::SameLine();
    keep_input("##keepvalue", &g_settings.keep_treasury_value, KEEP_TREASURY_MAX, 150.0f);
    note("money:keepvalue", std::to_string(g_settings.keep_treasury_value));
    ImGui::SameLine();
    ImGui::TextUnformatted("백만 달러");
    help("help:money", "켜 두면 국고가 이 금액보다 적어질 때 이 금액으로 올린다(0.5초마다). 창을 닫아도, 새 판에서도 계속된다");
    return true;
}

// 물자 탭의 한 줄에 놓이는 단추 다섯: 그 칸(또는 ALL_STOCK)의 재고에서 빼고, 0 으로 만들고, 더한다.
void stock_buttons(const std::string &name, int slot)
{
    static const struct {
        const char *label, *id;
        Change change;
        double amount;
    } BUTTONS[] = {
        {"-1억", ":-100m", Change::Add, -1e8}, {"-100만", ":-1m", Change::Add, -1e6}, {"0", ":zero", Change::Set, 0.0},
        {"+100만", ":+1m", Change::Add, 1e6}, {"+1억", ":+100m", Change::Add, 1e8},
    };
    for (size_t i = 0; i < sizeof(BUTTONS) / sizeof(BUTTONS[0]); i++) {
        if (i > 0)
            ImGui::SameLine();
        const bool pressed = ImGui::Button(BUTTONS[i].label);
        note(name + BUTTONS[i].id, BUTTONS[i].label);
        if (pressed)
            g_notice = keeper_enqueue({slot, BUTTONS[i].change, BUTTONS[i].amount}) ? "" : "대기 중인 요청이 많아 받지 못했습니다.";
    }
}

// 물자 탭의 한 줄. slot 이 ALL_STOCK 이면 "모든 물자" 줄이다(재고 표시와 최소 유지가 없다).
// 이번 판에서 쓰지 않는 물자의 줄(최소 유지가 켜져 있어 남은 것)은 단추가 꺼져 있다.
void stock_row(int slot, const GameValues &now, bool blocked)
{
    const bool all = slot == ALL_STOCK;
    const bool unused = !all && now.ok && !now.used[slot];
    const std::string name = all ? std::string("stock:all") : "stock:" + std::to_string(slot);
    const std::string label = all ? std::string("모든 물자") : product_label(slot);
    const std::string have = all || !now.ok ? std::string("-") : unused ? std::string("쓰지 않음") : short_amount(now.stock[slot]);
    ImGui::PushID(slot);
    ImGui::TableNextRow();
    ImGui::TableNextColumn();
    ImGui::AlignTextToFramePadding();
    ImGui::TextUnformatted(label.c_str());
    note(name, label);
    ImGui::TableNextColumn();
    ImGui::AlignTextToFramePadding();
    ImGui::TextUnformatted(have.c_str());
    note(name + ":now", have);
    ImGui::TableNextColumn();
    ImGui::BeginDisabled(blocked || !now.ok || unused);
    stock_buttons(name, slot);
    ImGui::EndDisabled();
    ImGui::TableNextColumn();
    if (!all) {                                  // 최소 유지는 설정이다 — 단추가 꺼져 있을 때도 고칠 수 있다
        if (ImGui::Checkbox("##keep", &g_settings.keep_stock[slot]))
            send_keep(true);
        note(name + ":keep", g_settings.keep_stock[slot] ? "1" : "0");
        ImGui::SameLine();
        keep_input("##keepvalue", &g_settings.keep_stock_value[slot], KEEP_STOCK_MAX, 120.0f);
        note(name + ":keepvalue", std::to_string(g_settings.keep_stock_value[slot]));
    }
    ImGui::PopID();
}

// 물자 탭: 내장 치트를 거치지 않고 플레이어의 물자 재고를 직접 고친다. 물자마다 한 줄 —
// 게임 안에서는 이번 판에서 쓰는 물자만, 게임 밖에서는 이름표에 있는 물자가 나온다(단추는 꺼져 있다).
// 최소 유지가 켜진 물자는 어느 쪽에서든 줄이 남는다(끌 수 있게). 쓸 수 있으면 true.
bool stock_tab(const GameState &game, bool blocked)
{
    GameValues now;
    if (!values_ready(game, "stock:off", &now))
        return false;
    ImGui::TextDisabled("재고는 0 아래로 내려가지 않는다. 다른 나라의 재고는 건드리지 않는다");
    help("help:stock", "최소 유지를 켜 두면 재고가 그 수량보다 적어질 때 그 수량으로 올린다(0.5초마다). 창을 닫아도, 새 판에서도 계속된다");
    const ImGuiTableFlags flags = ImGuiTableFlags_SizingFixedFit | ImGuiTableFlags_RowBg | ImGuiTableFlags_BordersInnerV
        | ImGuiTableFlags_ScrollX | ImGuiTableFlags_ScrollY;   // 창이 좁으면 표가 가로로 구른다
    if (!ImGui::BeginTable("stock", 4, flags))
        return true;
    ImGui::TableSetupScrollFreeze(1, 1);                       // 이름 칸과 머리 줄은 굴려도 남는다
    ImGui::TableSetupColumn("물자");
    ImGui::TableSetupColumn("재고");
    ImGui::TableSetupColumn("빼기 / 더하기");
    ImGui::TableSetupColumn("최소 유지");
    ImGui::TableHeadersRow();
    stock_row(ALL_STOCK, now, blocked);
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        if ((now.ok ? now.used[slot] : find_product(slot) != nullptr) || g_settings.keep_stock[slot])
            stock_row(slot, now, blocked);
    ImGui::EndTable();
    return true;
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
    const std::string state = !game.known ? "게임 상태를 읽을 수 없습니다 — 글쇠 방식으로 동작합니다"
        : game.multiplayer ? "멀티플레이에서는 동작하지 않습니다"
        : !game.in_game ? "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"
        : "플레이 중: " + region_label(game.player) + " (" + std::to_string(game.player) + ")";
    const std::string text = state + keep_text(game);   // 최소 유지가 켜져 있으면 늘 보인다 — 켜 둔 것을 잊지 않게
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
    send_keep(false);             // 저장해 둔 최소 유지를 keeper 에 넘긴다 — 창을 한 번도 열지 않아도 돈다
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
    // 물자 탭의 표(물자 열하나 + "모든 물자")가 굴리지 않아도 다 보이는 크기. 이미 써 본 사용자의 창은 저장된 크기 그대로다
    ImGui::SetNextWindowSize(ImVec2(720.0f, 600.0f), ImGuiCond_FirstUseEver);
    // 창은 구르지 않는다. 구르는 것은 탭의 내용(body)뿐이다 — 맨 위의 상태 줄 · 고른 나라와 바닥의 알림은 늘 보인다
    if (ImGui::Begin("SR2030 ToyBox", nullptr, ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoScrollWithMouse)) {
        const GameState game = game_state();
        const bool faulted = runner_faulted();
        const bool blocked = faulted || (game.known && (!game.in_game || game.multiplayer));
        const std::string trouble = runner_notice();
        if (faulted) {   // 맨 위에, 빨갛게: 게임의 상태가 어긋났을 수 있다 — 저장하지 말라는 말이 가려지면 안 된다
            ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 0.4f, 0.4f, 1.0f));
            ImGui::TextWrapped("%s", trouble.c_str());
            ImGui::PopStyleColor();
            note("fault", trouble);
        } else {
            status_line(game);
        }
        if (g_footer <= 0.0f)
            g_footer = 3.0f * ImGui::GetTextLineHeightWithSpacing();   // 첫 프레임의 어림. 그 뒤로는 지난 프레임에 잰 값
        const ImVec2 body(0.0f, -g_footer);
        bool values_tab = false, values_ok = false;         // 지금 보이는 탭이 값을 직접 쓰는 탭(돈 · 물자)인가, 그 탭을 쓸 수 있는가
        if (ImGui::BeginTabBar("tabs")) {
            const bool money = ImGui::BeginTabItem("돈");   // 첫 탭. 기능 표에 없다 — 내장 치트 없이 직접 한다
            note("tab:돈", "돈");
            if (money) {
                values_tab = true;
                if (ImGui::BeginChild("body", body))
                    values_ok = money_tab(game, blocked);
                ImGui::EndChild();
                ImGui::EndTabItem();
            }
            const bool stock = ImGui::BeginTabItem("물자");   // 둘째 탭. 이것도 기능 표에 없다
            note("tab:물자", "물자");
            if (stock) {
                values_tab = true;
                if (ImGui::BeginChild("body", body))
                    values_ok = stock_tab(game, blocked);
                ImGui::EndChild();
                ImGui::EndTabItem();
            }
            const char *tab = nullptr;
            for (int i = 0; i < FEATURE_COUNT; i++) {
                if (tab != nullptr && strcmp(tab, FEATURES[i].tab) == 0)
                    continue;   // 이 탭은 앞에서 그렸다(같은 탭의 기능은 표에서 이어져 있다)
                tab = FEATURES[i].tab;
                const bool open = ImGui::BeginTabItem(tab);
                note(std::string("tab:") + tab, tab);
                if (!open)
                    continue;
                const bool diplomacy = strcmp(tab, DIPLOMACY_TAB) == 0;
                const bool usable = !diplomacy || game.known;   // 이번 게임의 나라 목록을 모르면 이 탭은 쓰지 못한다
                RegionView view;
                if (diplomacy && usable)
                    view = choose(game);   // "고른 나라" 줄은 구르는 내용 밖에 둔다
                if (ImGui::BeginChild("body", body)) {
                    if (!usable) {
                        ImGui::TextWrapped("게임 상태를 읽을 수 있을 때만 씁니다.");
                    } else {
                        ImGui::BeginDisabled(blocked);
                        if (diplomacy)
                            picker(view);
                        for (int j = i; j < FEATURE_COUNT && strcmp(FEATURES[j].tab, tab) == 0; j++)
                            row(FEATURES[j], game);
                        ImGui::EndDisabled();
                    }
                }
                ImGui::EndChild();
                ImGui::EndTabItem();
            }
            if (ImGui::BeginTabItem("설정")) {
                if (ImGui::BeginChild("body", body))
                    settings_tab();
                ImGui::EndChild();
                ImGui::EndTabItem();
            }
            ImGui::EndTabBar();
        }
        const float top = ImGui::GetCursorPosY();
        ImGui::Separator();
        const int pending = runner_pending();
        const std::string last = runner_last();
        if (pending > 0)
            ImGui::Text("넣는 중: %s (남은 것 %d)", last.c_str(), pending);
        else if (!last.empty())
            ImGui::Text("마지막으로 넣은 것: %s", last.c_str());
        const std::string wrote = keeper_last();
        if (!wrote.empty()) {
            ImGui::Text("마지막으로 쓴 값: %s", wrote.c_str());
            note("wrote", wrote);
        }
        const std::string unwritten = keeper_notice();
        if (!unwritten.empty()) {
            ImGui::TextWrapped("%s", unwritten.c_str());
            note("unwritten", unwritten);
        }
        if (!g_notice.empty()) {
            ImGui::TextWrapped("%s", g_notice.c_str());
            note("notice", g_notice);
        }
        if (!faulted && !trouble.empty()) {
            ImGui::TextWrapped("%s", trouble.c_str());
            note("trouble", trouble);
        }
        // 게임 화면에 무슨 일이 생기는지. 게임을 읽을 수 있으면 게임 밖에서는 단추가 꺼져 있으므로(상태 줄이 그렇게 말한다) 띄우지 않는다.
        // 직접 실행에서는 게임의 설정 창이 뜨지 않는 대신, 열려 있던 패널이 스스로 다시 그려지지 않는다 — 일시 정지 중에도,
        // 시간이 흐르는 중에도(같은 날 안에서) [확인: 게임]
        // 값을 직접 쓰는 탭(돈 · 물자)은 글쇠 방식과 상관없다 — 쓸 수 있으면 늘 바로 바뀌고, 쓸 수 없으면 탭의 까닭 한 줄이 전부다.
        const char *const direct = "값은 바로 바뀝니다. 게임 화면의 숫자는 그 패널을 누르거나 다시 열 때 따라옵니다.";
        const char *const hint = game.known && blocked ? nullptr
            : values_tab ? (values_ok ? direct : nullptr)
            : game.known && runner_direct() ? direct
            : "단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.";
        if (hint != nullptr) {
            ImGui::TextWrapped("%s", hint);
            note("hint", hint);
        }
        if (!game.known && !values_tab)   // 게임을 읽지 못하면 내장 치트로 도는 단추를 끌 수 없다
            ImGui::TextWrapped("게임을 진행하는 중에만 누르십시오. 메뉴나 로비에서는 글자가 다른 곳에 들어갈 수 있습니다.");
        g_footer = ImGui::GetCursorPosY() - top;
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
