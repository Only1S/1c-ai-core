// Запуск Python из модов — единственный путь: «python» напрямую из мода не запускать (сверяет contour-tests §76)
import type { EngineInterface, ProcessRunInit, ProcessRunResult } from 'claude-code'

// cmd разбирает их сам: & и | режут команду, % раскрывает переменные; кавычки движка от % не спасают
const CMD_UNSAFE = /[&|<>^%!"]/

/** Псевдоним из WindowsApps первым в PATH движок не запускает («failed to start»), а через cmd он работает, как у хуков.
 *  Обходной путь не берёт аргумент со спецсимволом cmd и не ищет python в текущей папке: там может лежать чужой python.bat. */
export async function runPython (run: EngineInterface['process']['run'], args: readonly string[], init: ProcessRunInit): Promise<ProcessRunResult> {
  try {
    return await run(['python', ...args], init)
  } catch (err) {
    if (!String(err).includes('failed to start')) throw err
    if (args.some(a => CMD_UNSAFE.test(a))) throw new Error('ones-core: python не запустился, а обойти через cmd нельзя: спецсимвол в аргументе')
    return run(['cmd', '/d', '/c', 'python', ...args], { ...init, env: { ...init.env, NoDefaultCurrentDirectoryInExePath: '1' } })
  }
}
