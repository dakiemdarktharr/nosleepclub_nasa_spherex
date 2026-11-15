(() => {
  "use strict";
  const copy = {
    brand: ["SPHEREx đã thấy gì?", "What Did SPHEREx See?"],
    skipPublic: ["Đến nội dung", "Skip to content"],
    guideTitle: ["Cách sử dụng ↓", "How to use ↓"],
    guideHeading: ["Cách sử dụng", "How to use"],
    openSky: ["Mở bầu trời ↗", "Open the sky ↗"],
    guideOne: ["Mở bầu trời từ Trái Đất", "Open the sky from Earth"],
    guideOneDetail: ["Bấm Trái Đất. Trên màn hình cảm ứng, chạm một lần để hiện nhãn, chạm lại để mở.", "Click Earth. On touchscreens, tap once to reveal the label and again to open."],
    guideTwo: ["Chọn vùng trời", "Choose a sky field"],
    guideTwoDetail: ["Kéo để đổi góc nhìn. Chọn một ngôi sao lấp lánh hoặc tên mục tiêu trong danh sách.", "Drag to look around. Select a shimmering star or a target name in the list."],
    guideThree: ["Xem ảnh toàn khung", "Inspect the full detector image"],
    guideThreeDetail: ["Mở ảnh lớn và xem thời điểm chụp. Chọn Chuỗi thời gian hoặc So ảnh A/B ngay trên thẻ.", "Enlarge the image and check the observation time. Choose Observation timeline or Compare A/B on the card."],
    guideFour: ["Phát lại các lần quan sát", "Play the observations"],
    guideFourDetail: ["Chọn 2, 3, 5 hoặc 10 lần quan sát để chuẩn bị chuỗi, rồi bấm Phát. Chọn từng mốc để dừng ở ảnh đó.", "Choose 2, 3, 5 or 10 observations to prepare a sequence, then press Play. Select a frame to pause on it."],
    guideFive: ["So ảnh A/B", "Compare A/B"],
    guideFiveDetail: ["Chọn một lần chụp cho mỗi bên. Phóng to hoặc kéo một bên để cả hai cùng dịch chuyển.", "Choose an observation for each side. Zoom or drag one image to move both together."],
    guidedOpen: ["Thử so ảnh có hướng dẫn", "Try a guided comparison"],
    guidedAnswer: ["Xem lời giải", "See the explanation"],
    guidedNote: ["Ghi chú riêng trên thiết bị", "Private note on this device"],
    guidedSave: ["Lưu ghi chú", "Save note"],
    guidedExport: ["Xuất JSON", "Export JSON"],
    guidedNext: ["Thử ca khác", "Try another case"],
    guidedRetry: ["Thử tải lại", "Retry loading"],
    guidedLoading: ["Đang mở ảnh SPHEREx đã lưu…", "Opening saved SPHEREx images…"],
    guidedError: ["Chưa mở được bài tập. Hãy thử tải lại.", "The activity could not open. Try loading again."],
    guidedCorrect: ["Bạn đã nhận ra dấu hiệu", "You identified the clue"],
    guidedExplain: ["Cùng xem dấu hiệu", "Review the clue"],
    guidedSaved: ["Đã lưu ghi chú cùng hai ảnh trên thiết bị này.", "Note saved with both observations on this device."],
    guidedSaveError: ["Thiết bị chưa lưu được ghi chú. Bạn có thể xuất JSON.", "The note could not be saved here. You can export it as JSON."],
    datasets: ["Bộ dữ liệu", "Datasets"],
    navigation: ["Điều hướng", "Navigation"],
    language: ["Chuyển sang tiếng Anh", "Switch to Vietnamese"],
    homeLink: ["SPHEREx đã thấy gì? · Trang chủ", "What Did SPHEREx See? · Home"],
    skyNav: ["sphere x night", "sphere x night"],
    learnTitle: ["sphere x learn", "sphere x learn"],
    learnHeading: ["Khám phá bầu trời cùng SPHEREx", "Explore the sky with SPHEREx"],
    learnIntro: ["Thử soi ánh sáng hồng ngoại, tìm lại một góc trời và xem ảnh thật kể được gì.", "Explore infrared light, revisit a patch of sky, and see what real images can tell you."],
    learnStart: ["Bắt đầu khám phá", "Start exploring"],
    learnQuiz: ["Làm quiz", "Take the quiz"],
    learnPhoneOpen: ["Mở trên điện thoại", "Open on your phone"],
    learnPhoneTitle: ["Quét bằng điện thoại", "Scan with your phone"],
    learnPhoneInstructions: ["Mở camera và quét mã QR để vào Sphere X Learn.", "Open your camera and scan the QR code to visit Sphere X Learn."],
    learnPhoneLink: ["Mở Sphere X Learn ↗", "Open Sphere X Learn ↗"],
    learnLessons: ["Ba bài khám phá", "Three explorations"],
    learnLoading: ["Đang mở bài học…", "Opening the lessons…"],
    learnError: ["Bài học chưa tải được. Bạn thử mở lại nhé.", "The lessons didn’t load. Try opening them again."],
    learnRetryLoad: ["Thử tải lại", "Try loading again"],
    searchTitle: ["sphere x search", "sphere x search"],
    gagooObject: ["Gagoo · mở sphere x learn. Kéo để di chuyển; trên cảm ứng, chạm hai lần để mở.", "Gagoo · open sphere x learn. Drag to move; on touchscreens, tap twice to open."],
    gagooHint: ["Kéo để bay · bấm để học", "Drag to float · click to learn"],
    aboutNav: ["Về SPHEREx", "About SPHEREx"],
    kicker: ["Đài quan sát hồng ngoại trên quỹ đạo", "An infrared observatory in orbit"],
    tagline: ["Từ quỹ đạo SPHEREx, xuống Trái Đất và nhìn lên những vùng trời vệ tinh đã chụp.", "From SPHEREx’s orbit, look back up from Earth at the places it has observed."],
    explore: ["Khám phá bầu trời", "Explore the sky"],
    aboutObject: ["Chọn vệ tinh để tìm hiểu SPHEREx", "Select the spacecraft to learn about SPHEREx"],
    earthObject: ["Chọn Trái Đất để khám phá bầu trời", "Select Earth to explore the night sky"],
    earth: ["Trái Đất", "Earth"],
    orbitalIllustration: ["Minh họa quỹ đạo · NASA / JPL-Caltech", "Orbit illustration · NASA / JPL-Caltech"],
    pauseMotion: ["Dừng chuyển động", "Pause motion"],
    resumeMotion: ["Bật chuyển động", "Resume motion"],
    backOrbit: ["← Về quỹ đạo", "← Back to orbit"],
    aboutTitle: ["Về nhiệm vụ SPHEREx", "About SPHEREx"],
    aboutIntro: ["SPHEREx là đài quan sát hồng ngoại của NASA. Từ quỹ đạo thấp, vệ tinh lập bản đồ bầu trời theo bước sóng để nghiên cứu các thiên hà, lịch sử vũ trụ và băng trong các vùng hình thành sao.", "SPHEREx is NASA’s infrared observatory. From low Earth orbit, it maps the sky by wavelength to study galaxies, the history of the universe, and ice in star-forming regions."],
    spectralBands: ["kênh phổ danh nghĩa", "nominal spectral channels"],
    infrared: ["bước sóng hồng ngoại", "infrared wavelengths"],
    shields: ["tấm chắn photon hình nón", "conical photon shields"],
    aboutExplanation: ["Ba lớp chắn photon giữ thiết bị đủ lạnh để ghi nhận nguồn hồng ngoại mờ. Quan sát lặp lại cùng một vùng ở các thời điểm và bước sóng khác nhau tạo nên dữ liệu để khám phá.", "Three photon shields help keep the instrument cold enough to see faint infrared sources. Repeated observations build up images of each field at different times and wavelengths."],
    spacecraftRef: ["Cấu tạo vệ tinh · JPL ↗", "Spacecraft engineering · JPL ↗"],
    eyesRef: ["Mở trong NASA Eyes ↗", "Open in NASA Eyes ↗"],
    animationRef: ["Hoạt họa nhiều góc ↗", "Multi-angle animation ↗"],
    orbitImage: ["Minh họa vệ tinh SPHEREx bay trên rìa Trái Đất", "Illustration of SPHEREx above Earth’s limb"],
    aboutCaption: ["Minh họa SPHEREx trên quỹ đạo · NASA/JPL-Caltech PIA26531", "SPHEREx in orbit illustration · NASA/JPL-Caltech PIA26531"],
    skyTitle: ["sphere x night", "sphere x night"],
    skyIntro: ["Kéo bầu trời hoặc chọn một mục tiêu để xem ảnh SPHEREx của vùng đó.", "Drag the sky or choose a target to see a SPHEREx image of that field."],
    markerLegend: ["Vùng có ảnh mẫu", "Fields with preview images"],
    zoomOut: ["Thu nhỏ", "Zoom out"],
    zoomIn: ["Phóng to", "Zoom in"],
    resetView: ["Về góc đầu", "Reset view"],
    skyCanvas: ["Vòm trời tương tác theo tọa độ xích đạo", "Interactive equatorial sky view"],
    skyGuide: ["Kéo hoặc dùng phím mũi tên để đổi hướng. Đường chân trời minh họa · tọa độ ICRS.", "Drag or use the arrow keys to look around. Illustrated horizon · ICRS coordinates."],
    skyCredits: ["Ảnh nền · NASA SVS ↗", "Star map · NASA SVS ↗"],
    findRegion: ["Tìm vùng quan sát", "Find an observed field"],
    searchLabel: ["Tên mục tiêu mẫu", "Example target name"],
    searchHint: ["Tìm tên mục tiêu mẫu", "Search example targets"],
    noTargets: ["Thử tên khác, hoặc mở tìm theo tọa độ.", "Try another name or search by coordinates."],
    enterCoordinates: ["Nhập tọa độ RA / Dec →", "Enter RA / Dec →"],
    searchCenter: ["Tìm ảnh tại tâm ngắm", "Find images at the crosshair"],
    observedField: ["Ảnh quan sát SPHEREx", "SPHEREx observation"],
    compareImages: ["So sánh ảnh", "Compare images"],
    compareAB: ["So ảnh A/B", "Compare A/B"],
    observationTimeline: ["Chuỗi thời gian", "Observation timeline"],
    darkTheme: ["Chuyển sang chế độ tối", "Switch to dark mode"],
    lightTheme: ["Chuyển sang chế độ sáng", "Switch to light mode"],
    archivedSequence: ["Mở chuỗi ảnh đã lưu", "Open saved sequence"],
    archivedTitle: ["Epsilon Indi B · chuỗi DR1 đã lưu", "Epsilon Indi B · saved DR1 sequence"],
    archivedDescription: ["Ba ảnh SPHEREx DR1 D6 đã lưu dùng cùng lưới WCS và thang hiển thị. Chuỗi này dùng để xem vùng trời, chưa xác nhận chuyển động hay biến quang.", "Three saved SPHEREx DR1 D6 images share a WCS grid and display scale. Use them to view the field. Motion and variability remain unconfirmed."],
    archivedPlay: ["Phát chuỗi", "Play sequence"],
    archivedPause: ["Tạm dừng", "Pause"],
    archivedPrev: ["Ảnh trước", "Previous image"],
    archivedNext: ["Ảnh sau", "Next image"],
    archivedFits: ["FITS khung đang xem ↗", "Current frame FITS ↗"],
    archivedMetadata: ["Nguồn và thông số JSON ↗", "Sources and settings JSON ↗"],
    archivedLoading: ["Đang mở ba ảnh đã lưu…", "Opening three saved images…"],
    archivedError: ["Chưa mở được chuỗi đã lưu. Hãy đóng hộp thoại và thử lại.", "The saved sequence could not open. Close this dialog and try again."],
    sequenceCountLabel: ["Số khung trong chuỗi", "Frames in sequence"],
    sequenceCount2: ["2 khung", "2 frames"],
    sequenceCount3: ["3 khung", "3 frames"],
    sequenceCount5: ["5 khung", "5 frames"],
    sequenceCount10: ["10 khung", "10 frames"],
    sequencePrepare: ["Chuẩn bị chuỗi", "Prepare sequence"],
    fullFrame: ["FITS gốc cả detector ↗", "Full detector FITS ↗"],
    fullFieldLimit: ["Ảnh toàn detector đã giảm độ phân giải và kéo sáng riêng. Vòng xanh đánh dấu tâm dùng để tìm các ảnh DR1 cho cả hai chế độ.", "Downsampled, individually stretched full detector image. The blue circle marks the center of the DR1 search for both viewing modes."],
    enlargeImage: ["Mở ảnh lớn", "Open larger image"],
    close: ["Đóng", "Close"],
    team: ["Dự án độc lập của NoSleepClub", "An independent NoSleepClub project"],
    irsaSource: ["Kho dữ liệu NASA/IPAC IRSA ↗", "NASA/IPAC IRSA archive ↗"],
    researchNav: ["Tài liệu kiểm chứng", "Validation reports"],
    loadingFields: ["Đang mở danh sách vùng mẫu…", "Opening example fields…"],
    fieldsUnavailable: ["Tạm thời chưa tải được vùng mẫu. Bạn có thể tìm theo tọa độ.", "Example fields are unavailable. You can still search by coordinates."],
    loadingPreview: ["Đang tải ảnh mẫu…", "Loading preview…"],
    previewUnavailable: ["Tạm thời chưa tải được ảnh mẫu. Bạn có thể tìm ảnh DR1 cho vùng này.", "This preview is unavailable. You can search DR1 for this field."],
    workspaceLoading: ["Đang mở công cụ so ảnh…", "Opening the comparison workspace…"],
    workspaceError: ["Chưa mở được công cụ. Hãy tải lại trang để thử lại.", "The workspace could not open. Reload the page to try again."],
    reloadPage: ["Tải lại trang", "Reload page"],
    serviceStatus: ["Trạng thái dịch vụ", "Service status"],
    retryFields: ["Tải lại danh sách vùng trời", "Retry sky fields"],
    skyFallback: ["Dùng danh sách mục tiêu để chọn vùng.", "Use the target list to choose a field."]
  };

  const supported = (value) => value === "en" || value === "vi";
  const key = "spherex.language";
  const storedLanguage = () => {
    try { return localStorage.getItem(key); } catch { return null; }
  };
  const requested = new URL(location.href).searchParams.get("lang");
  const saved = storedLanguage();
  let language = supported(requested) ? requested : supported(saved) ? saved : "vi";
  document.documentElement.lang = language;
  const themeKey = "spherex.theme";
  let theme = "dark";
  try { if (localStorage.getItem(themeKey) === "light") theme = "light"; } catch { /* Default to dark. */ }
  document.documentElement.dataset.theme = theme;

  function text(id) {
    return copy[id]?.[language === "en" ? 1 : 0] || id;
  }

  function apply(next) {
    if (supported(next)) language = next;
    document.documentElement.lang = language;
    for (const el of document.querySelectorAll("[data-copy]")) el.textContent = text(el.dataset.copy);
    for (const el of document.querySelectorAll("[data-label]")) el.setAttribute("aria-label", text(el.dataset.label));
    for (const el of document.querySelectorAll("[data-placeholder]")) el.placeholder = text(el.dataset.placeholder);
    for (const el of document.querySelectorAll("[data-language]")) {
      el.textContent = language === "en" ? "Tiếng Việt" : "English";
      el.lang = language === "en" ? "vi" : "en";
    }
    applyTheme();
    window.SpherexWorkspaceLanguage?.apply(language);
    document.dispatchEvent(new CustomEvent("spherex:language", {detail: {language}}));
  }

  function applyTheme() {
    document.documentElement.dataset.theme = theme;
    const label = text(theme === "light" ? "darkTheme" : "lightTheme");
    for (const button of document.querySelectorAll("[data-theme-toggle]")) {
      button.setAttribute("aria-label", label);
      button.title = label;
      button.firstElementChild.textContent = theme === "light" ? "☾" : "☀";
    }
  }

  window.SpherexSite = {text, apply, language: () => language};
  document.addEventListener("DOMContentLoaded", () => {
    apply(language);
    for (const button of document.querySelectorAll("[data-theme-toggle]")) {
      button.addEventListener("click", () => {
        theme = theme === "dark" ? "light" : "dark";
        try { localStorage.setItem(themeKey, theme); } catch { /* The current page retains the setting. */ }
        applyTheme();
      });
    }
    for (const button of document.querySelectorAll("[data-language]")) {
      button.addEventListener("click", () => {
        const next = language === "en" ? "vi" : "en";
        const url = new URL(location.href);
        url.searchParams.set("lang", next);
        history.replaceState(history.state, "", url);
        try { localStorage.setItem(key, next); } catch { /* The URL keeps the setting. */ }
        apply(next);
      });
    }
  });
})();
