// Grades an output file with the official JS engine extracted from the contest sandbox.
// Usage: node grade.js <sandbox-level-6.html> <in_level-6_X.txt> <out_level-6_X.txt>
// The line ranges below match the 42nd CCC sandbox; adjust them for other editions.
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8').split('\n');
const consts = html.slice(708, 714).join('\n');
const body = html.slice(756, 1182).join('\n');
const make = new Function(consts + '\nconst gameState = { radius: 0, pattern: {}, emitter: {}, program: [], acceptedPatterns: 0 };\n' + body +
  '\nreturn { gameState, parseHexInput, parseHexSolution, precomputeStates };');
const eng = make();
const inp = fs.readFileSync(process.argv[3], 'utf8').replace(/\r/g, '').split('\n');
const out = fs.readFileSync(process.argv[4], 'utf8').replace(/\r/g, '').split('\n\n').filter(s => s.trim());
const n = +inp[0];
let i = 1, fails = 0, score = 0;
for (let k = 0; k < n; k++) {
  while (!inp[i].trim()) i++;
  const [R, rows, cols, cnt] = inp[i].trim().split(/\s+/).map(Number);
  const text = inp.slice(i, i + 1 + rows).join('\n');
  i += 1 + rows;
  eng.parseHexInput(eng.gameState, text);
  eng.parseHexSolution(eng.gameState, out[k]);
  eng.precomputeStates();
  const st = eng.gameState.precomputedStates;
  const acc = st.length ? st[st.length - 1].acceptedPatterns : 0;
  score += eng.gameState.program.length;
  if (acc < cnt) { fails++; if (fails <= 5) console.log('FAIL pattern', k, 'R', R, 'count', cnt, 'accepted', acc); }
}
console.log('patterns', n, 'programs', out.length, 'failures', fails, 'lines', score);
