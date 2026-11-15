import {lessons} from './assets/learn/lessons.js?v=1';

// The ship teaches the same first lesson as the book. Its quiz is deliberately
// limited to concepts taught there; rewards are game items, not science results.
export const lessonOne = lessons[0];
const scanSource = 'https://science.nasa.gov/photojournal/spherex-scans-the-sky/';
const iceSource = 'https://science.nasa.gov/photojournal/nasas-spherex-mission-maps-water-ice-throughout-cygnus-x/';

export const missionQuestions = [
  {
    id: 'infrared-light',
    prompt: {vi: 'Loại ánh sáng nào trong bài 1 được SPHEREx đo nhưng mắt mình không nhìn thấy?', en: 'Which kind of light in lesson 1 does SPHEREx measure even though our eyes cannot see it?'},
    choices: [
      {vi: 'Ánh sáng hồng ngoại.', en: 'Infrared light.'},
      {vi: 'Màu xanh lá cây trên màn hình.', en: 'The green color on the screen.'},
      {vi: 'Màu đỏ trên màn hình.', en: 'The red color on the screen.'},
    ],
    answer: 0,
    explanation: {vi: 'SPHEREx đo ánh sáng hồng ngoại. Màu đỏ, xanh và những màu khác trên ảnh hiển thị giúp mình nhìn thấy sự khác nhau giữa các dải hồng ngoại.', en: 'SPHEREx measures infrared light. Red, green, and other display colors help us see differences between infrared bands.'},
    source: scanSource,
  },
  {
    id: 'same-sky-patch',
    prompt: {vi: 'Khi chọn A, B rồi C trong mô hình của bài học, điều gì vẫn giữ nguyên?', en: 'When you choose A, B, and then C in the lesson model, what stays the same?'},
    choices: [
      {vi: 'Dải ánh sáng được bộ lọc cho đi qua.', en: 'The band of light passed by the filter.'},
      {vi: 'Vùng trời mà chấm trong mô hình tượng trưng.', en: 'The patch of sky represented by the dot.'},
      {vi: 'Độ rõ của đám bụi trong mọi ảnh.', en: 'How clearly the dust cloud appears in every image.'},
    ],
    answer: 1,
    explanation: {vi: 'Chấm vẫn tượng trưng cho cùng một vùng trời. A, B và C là các phần bộ lọc khác nhau trong mô hình minh họa, cho qua các dải ánh sáng khác nhau.', en: 'The dot still represents the same patch of sky. A, B, and C are different filter positions in the illustrative model, passing different bands of light.'},
    source: scanSource,
  },
  {
    id: 'another-band',
    prompt: {vi: 'SPHEREx đã chụp một vùng trời qua phần A của bộ lọc. Chụp lại qua phần B giúp kính biết thêm điều gì?', en: 'SPHEREx has photographed a patch of sky through part A of its filter. What can it learn by using part B?'},
    choices: [
      {vi: 'Vùng trời trông ra sao khi phóng to.', en: 'What the patch looks like at higher magnification.'},
      {vi: 'Chắc chắn vùng trời đã sáng lên theo thời gian.', en: 'That the patch has definitely brightened over time.'},
      {vi: 'Kính nhận được bao nhiêu ánh sáng ở một dải hồng ngoại khác.', en: 'How much light reaches the telescope in a different infrared band.'},
    ],
    answer: 2,
    explanation: {vi: 'Mỗi phần bộ lọc cho qua một dải khác nhau. Đổi từ A sang B bổ sung một phép đo hồng ngoại của cùng vùng trời; khác biệt giữa hai dải chưa đủ để kết luận vùng trời đã thay đổi theo thời gian.', en: 'Each filter position passes a different band. Moving from A to B adds an infrared measurement of the same patch; a difference between bands alone does not show that the sky changed over time.'},
    source: scanSource,
  },
  {
    id: 'overlapping-scan',
    prompt: {vi: 'Vì sao các ảnh chồng lên nhau khi SPHEREx quét bầu trời lại hữu ích?', en: 'Why is it useful that images overlap as SPHEREx scans the sky?'},
    choices: [
      {vi: 'Cùng một vùng trời đi qua nhiều phần bộ lọc để được đo ở nhiều dải.', en: 'The same patch passes through different filter positions to be measured in several bands.'},
      {vi: 'Để thay đổi vị trí thật của những ngôi sao.', en: 'To change the stars’ actual positions.'},
      {vi: 'Để biến ánh sáng hồng ngoại thành ánh sáng mắt thường nhìn thấy ngoài không gian.', en: 'To turn infrared light into light our eyes can see in space.'},
    ],
    answer: 0,
    explanation: {vi: 'Khi kính quét và các ảnh chồng lên nhau, cùng một vùng được nhìn qua nhiều phần bộ lọc. Các phép đo ở nhiều dải bổ sung thông tin về vùng đó.', en: 'As the telescope scans and the images overlap, the same patch is seen through different filter positions. Measurements in several bands add information about that patch.'},
    source: scanSource,
  },
  {
    id: 'display-colors',
    prompt: {vi: 'Trong video NASA, cùng một vùng trời hiện xanh ở ảnh này và đỏ ở ảnh khác. Hai màu đó biểu thị điều gì?', en: 'In NASA’s video, the same patch of sky appears green in one image and red in another. What do those colors represent?'},
    choices: [
      {vi: 'Hai màu mắt mình sẽ thấy nếu đến gần.', en: 'Two colors we would see with our own eyes up close.'},
      {vi: 'Hai dải hồng ngoại được NASA gán màu để hiển thị.', en: 'Two infrared bands that NASA assigned visible colors.'},
      {vi: 'Chắc chắn đó là hai mức nhiệt độ khác nhau.', en: 'Definitely two different temperatures.'},
    ],
    answer: 1,
    explanation: {vi: 'NASA gán màu mình thấy được cho các dải hồng ngoại. Đây là cách hiển thị dữ liệu, không phải màu mà mắt thường sẽ nhìn thấy ở vùng trời đó.', en: 'NASA assigns colors we can see to infrared bands. This is a way to display the data, not the colors our eyes would see in that patch of sky.'},
    source: scanSource,
  },
  {
    id: 'ice-signatures',
    prompt: {vi: 'Trong ví dụ Cygnus X ở bài 1, đo nhiều dải hồng ngoại giúp các nhà thiên văn tìm dấu hiệu của thứ gì?', en: 'In lesson 1’s Cygnus X example, measuring several infrared bands helps astronomers look for signs of what?'},
    choices: [
      {vi: 'Đường phố trên bề mặt một hành tinh.', en: 'Streets on the surface of a planet.'},
      {vi: 'Màu sơn thật của các ngôi sao.', en: 'The stars’ actual paint colors.'},
      {vi: 'Băng nước trong vùng đang hình thành sao.', en: 'Water ice in a region where stars are forming.'},
    ],
    answer: 2,
    explanation: {vi: 'Băng có dấu hiệu trong ánh sáng hồng ngoại. Đo nhiều dải giúp các nhà thiên văn tìm và lập bản đồ dấu hiệu băng nước ở Cygnus X; màu hiển thị riêng lẻ không đủ để tự xác nhận có băng.', en: 'Ice leaves signatures in infrared light. Measurements in several bands help astronomers find and map water-ice signatures in Cygnus X; a display color alone does not confirm ice.'},
    source: iceSource,
  },
];

/** Score one final set of first responses. Invalid/incomplete rounds never award.
 * The UI locks a response as soon as it is chosen; retries pass a new array.
 * This is a local learning-game score, not an authenticated reward ledger.
 */
export function evaluateMission(answers) {
  const total = missionQuestions.length;
  const valid = Array.isArray(answers) && answers.length === total &&
    missionQuestions.every((question, index) =>
      Object.hasOwn(answers, index) && Number.isInteger(answers[index]) &&
      answers[index] >= 0 && answers[index] < question.choices.length);
  if (!valid) return {score: 0, total, tier: 'none'};
  const score = missionQuestions.reduce((sum, question, index) => sum + Number(answers[index] === question.answer), 0);
  return {score, total, tier: score === total ? 'super' : score === total - 1 ? 'normal' : 'none'};
}
