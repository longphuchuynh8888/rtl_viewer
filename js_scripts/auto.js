"auto";
auto.waitFor();

// ========== CẤU HÌNH RULES (sửa trực tiếp ở đây) ==========
const RULES_CONFIG = {
    name: "Game + Ads Rules",
    checkInterval: 1200,          // ms giữa mỗi lần quét
    rules: [
        {
            name: "Close Ad - Skip/Close/X",
            priority: 10,
            logic: "AND",
            conditions: [
                { prop: "className", op: "equals", value: "android.widget.Button" },
                { prop: "text", op: "equals", value: "Install" },
            ],
            action: "click",
            waitAfter: 800
        },
        {
            name: "Close Ad - ImageView góc trên phải",
            priority: 9,
            logic: "AND",
            conditions: [
                { prop: "className", op: "contains", value: "ImageView" },
                { prop: "clickable", op: "equals", value: true }
            ],
            action: "click",
            region: "top-right",   // lọc vùng (tùy chọn)
            waitAfter: 600
        },
        {
            name: "Nút Play / Bắt đầu game",
            priority: 5,
            logic: "OR",
            conditions: [
                { prop: "text", op: "contains", value: "开始" },
                { prop: "text", op: "contains", value: "Play" },
                { prop: "text", op: "contains", value: "Start" },
                { prop: "desc", op: "contains", value: "play" },
                { prop: "desc", op: "contains", value: "start" }
            ],
            action: "click",
            waitAfter: 1000
        }
        // Thêm rule khác vào đây...
    ]
};

// ========== HÀM DUMP UI (dùng để phân tích) ==========
function dumpNode(node, depth, maxDepth) {
    if (!node || depth > maxDepth) return null;
    let bounds = node.bounds();
    let info = {
        text: node.text() || "",
        desc: node.desc() || "",
        id: node.id() || "",
        className: node.className() || "",
        packageName: node.packageName() || "",
        clickable: !!node.clickable(),
        bounds: bounds ? {
            left: bounds.left,
            top: bounds.top,
            right: bounds.right,
            bottom: bounds.bottom
        } : null,
        children: []
    };
    for (let i = 0; i < node.childCount(); i++) {
        let child = dumpNode(node.child(i), depth + 1, maxDepth);
        if (child) info.children.push(child);
    }
    return info;
}

function dumpCurrentUI(savePath) {
    let root = auto.root;
    if (!root) {
        toast("Không lấy được root");
        return null;
    }
    let data = dumpNode(root, 0, 10);
    if (savePath) {
        files.write(savePath, JSON.stringify(data, null, 2));
        toast("Đã lưu dump: " + savePath);
    }
    return data;
}

// ========== HÀM KHỚP ĐIỀU KIỆN ==========
function matchCondition(node, cond) {
    let val;
    switch (cond.prop) {
        case "text": val = node.text() || ""; break;
        case "desc": val = node.desc() || ""; break;
        case "id": val = node.id() || ""; break;
        case "className": val = node.className() || ""; break;
        case "packageName": val = node.packageName() || ""; break;
        case "clickable": val = !!node.clickable(); break;
        default: return false;
    }
    let strVal = String(val);
    switch (cond.op) {
        case "equals": return val === cond.value;
        case "contains": return strVal.indexOf(String(cond.value)) !== -1;
        case "startsWith": return strVal.startsWith(String(cond.value));
        case "endsWith": return strVal.endsWith(String(cond.value));
        case "matches": return new RegExp(cond.value).test(strVal);
        default: return false;
    }
}

function inRegion(node, region) {
    if (!region) return true;
    let b = node.bounds();
    if (!b) return false;
    let cx = b.centerX();
    let cy = b.centerY();
    let w = device.width;
    let h = device.height;
    if (region === "top-right") return cx > w * 0.7 && cy < h * 0.25;
    if (region === "top-left") return cx < w * 0.3 && cy < h * 0.25;
    if (region === "bottom") return cy > h * 0.75;
    if (region === "center") return cx > w * 0.3 && cx < w * 0.7 && cy > h * 0.3 && cy < h * 0.7;
    return true;
}

function findNodeByRule(root, rule) {
    function search(node) {
        if (!node) return null;
        let results = rule.conditions.map(c => matchCondition(node, c));
        let matched = rule.logic === "AND" ? results.every(Boolean) : results.some(Boolean);
        if (matched && inRegion(node, rule.region)) return node;
        for (let i = 0; i < node.childCount(); i++) {
            let found = search(node.child(i));
            if (found) return found;
        }
        return null;
    }
    return search(root);
}

// ========== HÀM THỰC THI HÀNH ĐỘNG ==========
function doAction(node, action) {
    if (!node) return false;
    let b = node.bounds();
    if (!b) return false;
    let x = b.centerX();
    let y = b.centerY();
    if (action === "click") {
        click(x, y);
        return true;
    } else if (action === "longClick") {
        longClick(x, y);
        return true;
    }
    return false;
}

// ========== ENGINE CHÍNH ==========
function runRules() {
    let rules = RULES_CONFIG.rules.slice().sort((a, b) => (b.priority || 0) - (a.priority || 0));
    toast("Bắt đầu quét rules...");
    console.show();

    while (true) {
        let root = auto.root;
        if (!root) {
            sleep(800);
            continue;
        }

        let acted = false;
        for (let rule of rules) {
            let node = findNodeByRule(root, rule);
            if (node) {
                if (doAction(node, rule.action || "click")) {
                    console.log("[" + rule.name + "] đã tương tác");
                    toast(rule.name);
                    sleep(rule.waitAfter || 500);
                    acted = true;
                    break; // chỉ làm 1 rule mỗi vòng
                }
            }
        }

        if (!acted) {
            // Không tìm thấy gì thì chờ
        }
        sleep(RULES_CONFIG.checkInterval || 1200);
    }
}

// ========== MENU ĐƠN GIẢN ==========
function showMenu() {
    let choice = dialogs.select("Chọn hành động", [
        "Chạy rules (tự động game + đóng quảng cáo)",
        "Dump UI hiện tại ra file",
        "Thoát"
    ]);
    if (choice === 0) {
        runRules();
    } else if (choice === 1) {
        let path = "/sdcard/scripts/dump_" + Date.now() + ".json";
        dumpCurrentUI(path);
    } else {
        exit();
    }
}

// ========== CHẠY ==========
showMenu();