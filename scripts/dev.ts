import type { CustomArgs, CustomOptions } from 'jsr:@ghostmind/run';
import { $ } from 'npm:zx@8';

// Checks that need no test framework: the package must compile, every theme
// must resolve to real files, and every theme must clear the contrast floor.
const APP = new URL('../app', import.meta.url).pathname.replace(/\/$/, '');

export default async function (_args: CustomArgs, opts: CustomOptions) {
  const { has } = opts;
  const python = Deno.env.get('THEME_PYTHON') ?? 'python3';

  $.env = { ...Deno.env.toObject(), PYTHONPATH: APP };
  $.verbose = true; // surface the python output - that IS the check result

  if (has('check')) {
    console.log('› compiling package');
    await $`${python} -m compileall -q ${APP}/theme`;
    console.log('› resolving every theme');
    await $`${python} -m theme doctor`;
  }

  if (has('test')) {
    console.log('› contrast audit');
    await $`${python} -m theme contrast`;
  }
}
