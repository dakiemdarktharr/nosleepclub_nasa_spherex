(() => {
  const $ = (id) => document.getElementById(id);
  let language = new URL(location.href).searchParams.get("lang") === "en" ? "en" : "vi";
  let result = null;
  let failed = false;
  let busy = false;
  const t = (vi, en) => language === "vi" ? vi : en;
  function render() {
    document.documentElement.lang = language;
    $("home").href = `/?lang=${language}`;
    $("language").textContent = language === "vi" ? "English" : "Tiếng Việt";
    $("title").textContent = t("Trạng thái dịch vụ", "Service status");
    $("scope").textContent = t("Kết quả kiểm tra tại thời điểm ghi bên dưới, được lưu tối đa một phút.", "Point-in-time check, cached for up to one minute.");
    $("data-label").textContent = t("Dữ liệu công khai", "Public data");
    $("data-state").textContent = busy ? t("Đang kiểm tra…", "Checking…") : failed ? t("Không kết nối được trang trạng thái. Hãy thử lại.", "Could not reach the status service. Try again.") : result?.public_data === "available" ? t("Đọc được dữ liệu mẫu và hash khớp", "Sample readable; hash verified") : t("Tạm thời không đọc được dữ liệu mẫu", "Sample temporarily unavailable");
    $("checked").textContent = result ? `${t("Kiểm tra lúc", "Checked at")}: ${result.checked_at_utc} · ${result.probe_ms} ms` : "";
    $("limits").textContent = t("Chỉ kiểm tra một tệp metadata công khai. Không đại diện cho mọi ảnh hoặc độ sẵn sàng liên tục.", "Checks one public metadata file. Does not certify every image or continuous uptime.");
    $("irsa-state").textContent = t("Chưa kiểm tra trong lần này. Khi dựng ảnh mới thất bại, hãy giữ ảnh đã tải và thử lại từ khung ảnh.", "Not checked in this probe. If a new cutout fails, keep loaded images and retry the affected pane.");
    $("reviews-label").textContent = t("Nhận xét riêng", "Private reviews");
    $("reviews-state").textContent = t("Không đọc nhận xét trong kiểm tra công khai này. Trạng thái lưu hiển thị tại nơi bạn ghi nhận xét.", "This public check does not read reviews. Save status appears where you record a note.");
    $("privacy").textContent = t("Không gửi email hoặc thông báo tự động. Trang này không hiển thị khóa truy cập hay nội dung nhận xét.", "No email or automatic notifications. Access keys and review contents are never shown here.");
    $("recent-label").textContent = t("Hoạt động API gần đây", "Recent API activity");
    $("recent").replaceChildren();
    for (const [key, vi, en] of [["data", "Đọc dữ liệu", "Data reader"], ["observations", "Tìm quan sát", "Observation search"], ["frame", "Dựng ảnh", "Cutout rendering"], ["reviews", "Lưu nhận xét", "Reviews"]]) {
      const item = document.createElement("li");
      const entry = result?.recent_activity?.[key];
      const success = entry?.last_success_at, error = entry?.last_error_at;
      item.textContent = `${t(vi, en)}: ` + (!entry ? t("chưa có ghi nhận", "no recorded activity") : [success && `${t("thành công", "success")} ${success}`, error && `${t("lỗi máy chủ", "server error")} ${error}`].filter(Boolean).join(" · "));
      $("recent").append(item);
    }
    $("refresh").textContent = t("Kiểm tra lại", "Check again");
    $("refresh").disabled = busy;
    $("checks").setAttribute("aria-busy", String(busy));
  }
  async function refresh() {
    if (busy) return;
    busy = true; failed = false; render();
    try {
      const response = await fetch("/api/status", {signal: AbortSignal.timeout(15000)});
      if (!response.ok) throw new Error("status_unavailable");
      result = await response.json();
    } catch { failed = true; }
    busy = false; render();
  }
  $("language").addEventListener("click", () => {
    language = language === "vi" ? "en" : "vi";
    const url = new URL(location.href); url.searchParams.set("lang", language);
    history.replaceState(null, "", url); render();
  });
  $("refresh").addEventListener("click", refresh);
  refresh();
})();
