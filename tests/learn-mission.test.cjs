const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');

(async () => {
  const {lessonOne, missionQuestions, evaluateMission} = await import(pathToFileURL(path.resolve('web/learn-mission.js')));
  const {lessons} = await import(pathToFileURL(path.resolve('web/assets/learn/lessons.js')) + '?v=1');
  assert.equal(lessonOne, lessons[0], 'ship lesson and library share one source');
  assert.equal(lessonOne.id, 'filters');
  assert.equal(missionQuestions.length, 6);
  assert.equal(new Set(missionQuestions.map(question => question.id)).size, 6);
  for (const question of missionQuestions) {
    assert.equal(question.choices.length, 3);
    assert.ok(Number.isInteger(question.answer) && question.answer >= 0 && question.answer < question.choices.length);
    for (const text of [question.prompt, question.explanation, ...question.choices]) {
      for (const language of ['vi', 'en']) assert.ok(typeof text[language] === 'string' && text[language].trim().length > 10);
      assert.notEqual(text.vi, text.en, 'each text has a real translation');
    }
    const source = new URL(question.source);
    assert.equal(source.hostname, 'science.nasa.gov');
    assert.ok(lessonOne.sources.some(item => item.url === question.source), 'source is available in the taught lesson');
  }
  const correct = missionQuestions.map(question => question.answer);
  for (let score = 0; score <= 6; score++) {
    const answers = missionQuestions.map((question, index) => index < score ? question.answer : (question.answer + 1) % question.choices.length);
    const snapshot = [...answers];
    assert.deepEqual(evaluateMission(answers), {score, total: 6, tier: score === 6 ? 'super' : score === 5 ? 'normal' : 'none'});
    assert.deepEqual(answers, snapshot, 'scoring must not mutate first responses');
  }
  for (const invalid of [undefined, null, {}, '012012', [], correct.slice(0, 5), [...correct, 0], new Array(6),
    [undefined, ...correct.slice(1)], [null, ...correct.slice(1)], ['0', ...correct.slice(1)],
    [NaN, ...correct.slice(1)], [Infinity, ...correct.slice(1)], [-1, ...correct.slice(1)],
    [3, ...correct.slice(1)], [0.5, ...correct.slice(1)]]) {
    assert.deepEqual(evaluateMission(invalid), {score: 0, total: 6, tier: 'none'}, 'invalid and incomplete rounds cannot award fuel');
  }
  const previous = missionQuestions.map(question => (question.answer + 1) % question.choices.length);
  assert.equal(evaluateMission(previous).tier, 'none');
  assert.equal(evaluateMission(correct).tier, 'super', 'a new complete attempt is scored independently');
  assert.equal(evaluateMission(previous).score, 0, 'a retry cannot alter the previous round');
  console.log('Learning mission: six bilingual sourced questions, every reward boundary, malformed rounds and retry isolation passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
