"auto";
auto.waitFor();

// ========== CẤU HÌNH ==========
const SCRIPT_URL = "https://raw.githubusercontent.com/longphuchuynh8888/rtl_viewer/refs/heads/main/js_scripts/auto.js"; 
// Đổi thành link raw của bạn (GitHub, Gist, server của bạn...)
const RELOAD_INTERVAL = 0; // 0 = chỉ tải 1 lần khi mở; >0 = reload lại sau X ms (ví dụ 300000 = 5 phút)
const LOCAL_CACHE = "/sdcard/scripts/cache_game_ads.js";

// ========== HÀM TẢI & CHẠY ==========
function downloadAndRun() {
    toast("Đang tải code mới...");
    try {
        let res = http.get(SCRIPT_URL, {
            headers: { "Cache-Control": "no-cache" }
        });
        if (res.statusCode !== 200) {
            toast("Tải thất bại: " + res.statusCode);
            return false;
        }
        let code = res.body.string();
        if (!code || code.length < 50) {
            toast("Code tải về không hợp lệ");
            return false;
        }

        // Lưu cache local (để chạy offline lần sau nếu cần)
        files.write(LOCAL_CACHE, code);
        toast("Đã tải xong, đang chạy...");

        // Chạy code vừa tải
        engines.execScript("remote_script", code);
        return true;
    } catch (e) {
        toast("Lỗi: " + e);
        // Fallback: chạy file cache nếu có
        if (files.exists(LOCAL_CACHE)) {
            toast("Chạy từ cache local");
            engines.execScriptFile(LOCAL_CACHE);
            return true;
        }
        return false;
    }
}

// ========== MENU ==========
function showMenu() {
    let options = [
        "Tải & chạy code mới từ online",
        "Chạy từ cache local (nếu có)",
        "Thoát"
    ];
    let choice = dialogs.select("Loader - Đồng bộ code", options);
    if (choice === 0) {
        downloadAndRun();
        if (RELOAD_INTERVAL > 0) {
            setInterval(downloadAndRun, RELOAD_INTERVAL);
        }
    } else if (choice === 1) {
        if (files.exists(LOCAL_CACHE)) {
            engines.execScriptFile(LOCAL_CACHE);
        } else {
            toast("Chưa có cache");
        }
    } else {
        exit();
    }
}

// Tự chạy ngay khi mở (bỏ comment nếu muốn)
// downloadAndRun();

showMenu();