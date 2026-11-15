export const lessons = [
  {
    id: "filters",
    minutes: 6,
    title: {
      vi: "Sao SPHEREx chụp lại cùng một vùng trời?",
      en: "Why does SPHEREx photograph the same patch of sky again?",
    },
    lead: {
      vi: "Trong video NASA, đám bụi hiện rõ ở vài ảnh của cùng một vùng trời. Bạn đoán điều gì thay đổi giữa các ảnh?",
      en: "In NASA’s video, a dust cloud stands out in some images of the same patch of sky. What do you think changes between images?",
    },
    steps: [
      {
        title: {vi: "Thử ba phần bộ lọc", en: "Try three parts of the filter"},
        text: {
          vi: "Chọn lần lượt A, B và C trong mô hình. Chấm tượng trưng cho một vùng trời. Mỗi phần bộ lọc cho một dải ánh sáng khác nhau đi qua, trong khi chấm vẫn ở nguyên chỗ.",
          en: "Choose A, B, and C in the model. The dot stands for a patch of sky. Each part of the filter lets through a different band of light while the dot stays put.",
        },
      },
      {
        title: {vi: "Đọc màu trong ảnh", en: "Read the colors in the image"},
        text: {
          vi: "Các ảnh SPHEREx chồng lên nhau khi kính quét bầu trời. Nhờ đó, cùng một vùng đi qua nhiều phần của bộ lọc. Kính đo ánh sáng hồng ngoại mà mắt mình không thấy được. NASA gán màu để mình phân biệt các dải trên màn hình.",
          en: "SPHEREx’s images overlap as it scans the sky. The same patch passes through different parts of the filter. The telescope measures infrared light, which our eyes can’t see. NASA assigns visible colors so we can tell the bands apart on screen.",
        },
      },
      {
        title: {vi: "Tìm dấu vết của băng", en: "Look for signs of ice"},
        text: {
          vi: "Có thứ hiện rõ hơn ở một số dải hồng ngoại. Đo nhiều dải giúp các nhà thiên văn tìm dấu hiệu của băng nước ở Cygnus X, một vùng đang hình thành sao.",
          en: "Some features stand out more in certain infrared bands. Measuring several bands helped astronomers find signs of water ice in Cygnus X, a region where stars are forming.",
        },
      },
    ],
    sources: [
      {
        url: "https://science.nasa.gov/photojournal/spherex-scans-the-sky/",
        label: {vi: "Video NASA về cách SPHEREx quét bầu trời", en: "NASA video of SPHEREx scanning the sky"},
      },
      {
        url: "https://science.nasa.gov/photojournal/nasas-spherex-mission-maps-water-ice-throughout-cygnus-x/",
        label: {vi: "Bản đồ băng nước ở Cygnus X", en: "Map of water ice in Cygnus X"},
      },
    ],
    questions: [
      {
        prompt: {
          vi: "SPHEREx đã chụp một vùng trời qua phần A của bộ lọc. Chụp lại qua phần B giúp kính biết thêm điều gì?",
          en: "SPHEREx has photographed a patch of sky through part A of its filter. What can it learn by using part B?",
        },
        choices: [
          {vi: "Vùng trời trông ra sao khi phóng to.", en: "What the patch looks like at higher magnification."},
          {vi: "Kính nhận được bao nhiêu ánh sáng ở một dải hồng ngoại khác.", en: "How much light reaches the telescope in a different infrared band."},
          {vi: "Vùng trời có sáng lên theo thời gian hay không.", en: "Whether the patch has brightened over time."},
        ],
        answer: 1,
        feedback: {
          vi: "Mỗi phần bộ lọc cho qua một dải khác nhau. Đổi từ A sang B giúp mình có thêm một phép đo hồng ngoại của cùng vùng trời.",
          en: "Each part of the filter lets through a different band. Switching from A to B gives us another infrared measurement of the same patch of sky.",
        },
      },
      {
        prompt: {
          vi: "Trong video NASA, cùng một vùng trời hiện xanh ở ảnh này và đỏ ở ảnh khác. Hai màu đó biểu thị điều gì?",
          en: "In NASA’s video, the same patch of sky appears green in one image and red in another. What do those colors represent?",
        },
        choices: [
          {vi: "Hai màu mắt mình sẽ thấy nếu đến gần.", en: "Two colors we would see with our own eyes up close."},
          {vi: "Hai mức nhiệt độ của vùng trời.", en: "Two temperatures of the patch of sky."},
          {vi: "Hai dải hồng ngoại được NASA gán màu để hiển thị.", en: "Two infrared bands that NASA assigned visible colors."},
        ],
        answer: 2,
        feedback: {
          vi: "NASA dùng màu mình thấy được để phân biệt những dải hồng ngoại mà mắt mình không nhìn thấy.",
          en: "NASA uses colors we can see to distinguish infrared bands that our eyes can’t see.",
        },
      },
    ],
  },
  {
    id: "nightsky",
    minutes: 6,
    title: {
      vi: "Bạn tìm lại được cụm chấm này không?",
      en: "Can you find the same group of dots again?",
    },
    lead: {
      vi: "Trong NightSky, bạn có thể lật qua ba ảnh SPHEREx thật của vùng Epsilon Indi B. Chọn một cụm chấm dễ nhớ rồi thử tìm lại nó qua từng ảnh.",
      en: "In NightSky, you can flip through three real SPHEREx images of the Epsilon Indi B field. Pick a group of dots you can remember and try to find it in each image.",
    },
    steps: [
      {
        title: {vi: "Mở chuỗi ảnh", en: "Open the image sequence"},
        text: {
          vi: "Trong NightSky, chọn Bộ dữ liệu, tìm Epsilon Indi B rồi chọn Mở chuỗi ảnh đã lưu.",
          en: "In NightSky, select Datasets, find Epsilon Indi B, and open its saved sequence.",
        },
      },
      {
        title: {vi: "Xem từng lần chụp", en: "Look at each observation"},
        text: {
          vi: "Bấm Phát chuỗi rồi Tạm dừng. Dùng Ảnh trước và Ảnh sau để tìm lại cụm chấm đã chọn. Ngày dưới ảnh giúp bạn biết lần nào được chụp trước.",
          en: "Select Play sequence, then Pause. Use Previous image and Next image to find your group of dots again. The date below each image tells you which one was taken first.",
        },
      },
      {
        title: {vi: "Chọn ảnh để so", en: "Choose images to compare"},
        text: {
          vi: "Muốn xem một chấm có thay đổi theo thời gian, hãy bắt đầu với ảnh cùng vùng, khác ngày và có bước sóng gần nhau. Chỉ cần đổi dải ánh sáng, cùng một vùng đã có thể trông khác.",
          en: "To look for a change over time, start with images of the same field taken on different dates at similar wavelengths. Changing the band alone can make the same patch look different.",
        },
      },
    ],
    sources: [
      {
        url: "assets/mission/epsilon-sequence/provenance.json",
        label: {vi: "Nguồn ảnh Epsilon Indi B", en: "Epsilon Indi B image provenance"},
      },
    ],
    questions: [
      {
        prompt: {
          vi: "Mở chuỗi Epsilon Indi B. Ảnh sớm nhất và ảnh muộn nhất được chụp vào hai ngày nào?",
          en: "Open the Epsilon Indi B sequence. On which dates were the earliest and latest images taken?",
        },
        choices: [
          {vi: "29/4 và 7/5.", en: "April 29 and May 7."},
          {vi: "29/4 và 1/5.", en: "April 29 and May 1."},
          {vi: "1/5 và 7/5.", en: "May 1 and May 7."},
        ],
        answer: 0,
        feedback: {
          vi: "Chuỗi có thể phát lặp. Bạn nhìn ngày dưới mỗi ảnh để tìm thứ tự chụp.",
          en: "The sequence can loop. Look at the dates below the images to find the order they were taken in.",
        },
      },
      {
        prompt: {
          vi: "Bạn muốn xem một chấm sáng có thay đổi theo thời gian. Bạn sẽ mở cặp ảnh nào trước?",
          en: "You want to see if a bright dot has changed over time. Which pair would you open first?",
        },
        choices: [
          {vi: "Cùng vùng, cùng ngày, hai dải hồng ngoại khác nhau.", en: "Same field and date, two different infrared bands."},
          {vi: "Cùng vùng, khác ngày, hai dải hồng ngoại khác xa nhau.", en: "Same field, different dates, two very different infrared bands."},
          {vi: "Cùng vùng, khác ngày, hai dải hồng ngoại gần nhau.", en: "Same field, different dates, two similar infrared bands."},
        ],
        answer: 2,
        feedback: {
          vi: "Khi dùng hai dải gần nhau, bạn giảm khả năng chấm trông khác chỉ vì kính đo ở bước sóng khác.",
          en: "Choosing similar bands reduces the chance that the dot looks different just because of the wavelengths the telescope measured.",
        },
      },
    ],
  },
  {
    id: "evidence",
    minutes: 7,
    title: {vi: "Chấm sáng biến mất thật à?", en: "Did the bright dot really disappear?"},
    lead: {
      vi: "Một ảnh có chấm sáng. Ảnh sau lại có ô tím ở đúng chỗ đó. Trước khi đoán chuyện gì đã xảy ra, mình xem chú giải nhé.",
      en: "One image shows a bright dot. The next has a purple pixel in exactly the same spot. Before guessing what happened, let’s check the legend.",
    },
    steps: [
      {
        title: {vi: "Đọc chú giải", en: "Read the legend"},
        text: {
          vi: "Ô tím là chỗ thiếu dữ liệu. Ô cam là ô ảnh bị loại khi kiểm tra chất lượng. Ô tối chỉ mức hiển thị thấp trên thang đang dùng.",
          en: "Purple marks missing data. Orange marks a pixel excluded in a quality check. A dark pixel has a low display level on the current scale.",
        },
      },
      {
        title: {vi: "Kiểm tra chỗ cần so", en: "Check the spot you want to compare"},
        text: {
          vi: "Khi so độ sáng, hãy kiểm tra cả hai ảnh có dữ liệu dùng được ở cùng vị trí. Thử đọc ô khoanh trong hai ảnh Epsilon Indi B trước khi sang vùng WISE 0855 ở phần quiz.",
          en: "To compare brightness, check that both images have usable data at the same location. Try reading the marked pixel in the Epsilon Indi B pair before moving on to WISE 0855 in the quiz.",
        },
      },
      {
        title: {vi: "Tìm mốc quanh chấm sáng", en: "Find landmarks around a bright dot"},
        text: {
          vi: "Nếu cả cụm chấm cùng lệch, hãy dùng các chấm xung quanh làm mốc để căn hai ảnh. Ảnh xem trước giúp bạn chọn chỗ đáng xem kỹ. Để xác nhận độ sáng hoặc vị trí thay đổi, mình cần kiểm tra số đo và sai số.",
          en: "If the whole group shifts, use the nearby dots as landmarks to align the images. A preview helps you decide where to look closer. Confirming a change in brightness or position takes measurements and a check of their uncertainty.",
        },
      },
    ],
    sources: [
      {
        url: "assets/mission/epsilon-sequence/provenance.json",
        label: {vi: "Nguồn ảnh Epsilon Indi B", en: "Epsilon Indi B image provenance"},
      },
      {
        url: "data/guided-transfer/provenance.json",
        label: {vi: "Nguồn ảnh vùng WISE 0855", en: "WISE 0855 field image provenance"},
      },
    ],
    questions: [
      {
        prompt: {
          vi: "Ô được khoanh trong ảnh A có màu cam, còn ảnh B có màu xám. Bạn sẽ ghi gì vào sổ quan sát?",
          en: "The marked pixel in image A is orange. In image B it is gray. What would you write in your observing notes?",
        },
        choices: [
          {vi: "Ô ở ảnh A đã bị loại. Cần thêm ảnh có dữ liệu dùng được ở chỗ đó để so độ sáng.", en: "The pixel in image A was excluded. We need another image with usable data at that spot to compare brightness."},
          {vi: "Chấm sáng mờ đi giữa hai lần chụp vì ô cam chuyển thành xám.", en: "The dot dimmed between observations because the pixel changed from orange to gray."},
          {vi: "Chấm đó sáng lên vì ảnh B hiện ô xám.", en: "The dot brightened because the pixel in image B is gray."},
        ],
        answer: 0,
        feedback: {
          vi: "Ô cam đánh dấu dữ liệu đã bị loại. Muốn so độ sáng, mình cần cả hai lần chụp có dữ liệu dùng được ở cùng vị trí.",
          en: "Orange marks excluded data. To compare brightness, we need usable data at the same location in both observations.",
        },
      },
      {
        prompt: {
          vi: "Thử tưởng tượng chấm bạn theo dõi và ba chấm bên cạnh đều lệch sang phải gần bằng nhau. Bạn làm gì để kiểm tra riêng chấm mình đang theo dõi?",
          en: "Imagine the dot you are tracking and three nearby dots all shift to the right by about the same amount. How would you check your dot on its own?",
        },
        choices: [
          {vi: "Đo khoảng cách từ chấm đó đến mép phải mỗi ảnh.", en: "Measure from the dot to the right edge of each image."},
          {vi: "Căn hai ảnh theo các chấm xung quanh rồi xem chấm đó còn lệch so với chúng không.", en: "Align the images using the nearby dots and see if your dot still shifts relative to them."},
          {vi: "Phóng to ảnh sau đến khi thấy chấm rõ nhất.", en: "Zoom into the second image until the dot is as clear as possible."},
        ],
        answer: 1,
        feedback: {
          vi: "Cả cụm cùng lệch là dấu hiệu hai ảnh có thể đang lệch nhau. Căn theo các chấm bên cạnh giúp bạn kiểm tra xem chấm mình theo dõi còn lệch không.",
          en: "When the whole group shifts, the images may be out of alignment. Matching the nearby dots lets you check whether your dot still appears to shift.",
        },
      },
    ],
  },
];
