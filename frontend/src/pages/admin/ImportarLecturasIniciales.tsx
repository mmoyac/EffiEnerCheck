import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Download, FileSpreadsheet, Upload } from 'lucide-react'
import { boletasApi } from '../../api/boletas'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Alert'
import { clp, numero } from '../../utils/format'
import type { ImportacionLecturasIniciales } from '../../types'

interface Props {
  open: boolean
  boletaId: number
  onClose: () => void
  onAplicada: () => void
}

/**
 * Carga masiva de la lectura inicial desde Excel (cambio lectura-inicial): subir → vista previa → aplicar.
 * Todo o nada: con errores no se aplica ninguna lectura.
 */
export function ImportarLecturasIniciales({ open, boletaId, onClose, onAplicada }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [vista, setVista] = useState<ImportacionLecturasIniciales | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [descargando, setDescargando] = useState(false)

  const cerrar = () => { setArchivo(null); setVista(null); setError(''); onClose() }

  const errorDe = (err: unknown) => {
    const detail = (err as AxiosError<{ detail: unknown }>)?.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object' && 'mensaje' in detail) return String((detail as { mensaje: string }).mensaje)
    return 'No se pudo procesar la planilla'
  }

  const revisar = async (f: File) => {
    setArchivo(f)
    setVista(null)
    setError('')
    setCargando(true)
    try {
      setVista(await boletasApi.importarLecturasIniciales(boletaId, f, false))
    } catch (err) {
      setError(errorDe(err))
    } finally {
      setCargando(false)
    }
  }

  const aplicar = async () => {
    if (!archivo) return
    setCargando(true)
    setError('')
    try {
      await boletasApi.importarLecturasIniciales(boletaId, archivo, true)
      onAplicada()
      cerrar()
    } catch (err) {
      setError(errorDe(err))
    } finally {
      setCargando(false)
    }
  }

  const reemplazos = vista?.a_aplicar.filter((f) => f.reemplaza).length ?? 0

  // Lecturas y saldos que cambian, juntos por parcela (una fila apilada cabe en el ancho de un celular)
  const cambios = (() => {
    if (!vista) return []
    const porParcela = new Map<string, { numero: string; orden: number; lectura?: { antes: number | null; despues: number; reemplaza: boolean }; saldo?: { antes: number | null; despues: number } }>()
    const fila = (numero: string) => {
      if (!porParcela.has(numero)) porParcela.set(numero, { numero, orden: porParcela.size })
      return porParcela.get(numero)!
    }
    vista.a_aplicar.forEach((f) => { fila(f.numero_parcela).lectura = { antes: f.valor_actual, despues: f.valor, reemplaza: f.reemplaza } })
    vista.saldos.forEach((f) => { fila(f.numero_parcela).saldo = { antes: f.valor_actual, despues: f.valor } })
    return [...porParcela.values()].sort((x, y) => x.numero.localeCompare(y.numero, 'es', { numeric: true, sensitivity: 'base' }))
  })()

  return (
    <Modal open={open} onClose={cerrar} title="Cargar lecturas iniciales desde Excel" size="xl">
      <div className="space-y-4">
        <p className="text-sm text-slate-300">
          Usa la plantilla (botón «Descargar plantilla»): columnas <strong>Parcela</strong>, <strong>Lectura inicial</strong> y,
          opcional, <strong>Saldo luz</strong> (la deuda por luz anterior a la plataforma, que abre la cuenta corriente).
          Las celdas vacías se omiten; un saldo en 0 deja la parcela sin deuda. Primero verás una vista previa; nada se guarda hasta que presiones «Aplicar».
        </p>

        <Button size="sm" variant="secondary" disabled={descargando}
                onClick={async () => {
                  setDescargando(true)
                  try { await boletasApi.descargarPlantillaLecturasIniciales(boletaId, 'lecturas-iniciales.xlsx') }
                  catch { setError('No se pudo descargar la plantilla') }
                  finally { setDescargando(false) }
                }}>
          <Download className="h-4 w-4" /> Descargar plantilla (parcelas, lectura inicial y saldo luz)
        </Button>

        <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-slate-600 py-5 text-sm text-slate-300 hover:border-primary-500">
          <FileSpreadsheet className="h-5 w-5 text-primary-400" />
          {archivo ? archivo.name : 'Elegir planilla .xlsx'}
          <input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" className="hidden"
                 onChange={(e) => { const f = e.target.files?.[0]; if (f) revisar(f); e.target.value = '' }} />
        </label>

        {error && <Alert variant="error">{error}</Alert>}

        {vista && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
              <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-500">Lecturas / saldos</p><p className="text-lg font-bold text-slate-100">{vista.a_aplicar.length} / {vista.saldos.length}</p></div>
              <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-500">Reemplazan una tomada</p><p className={`text-lg font-bold ${reemplazos ? 'text-yellow-300' : 'text-slate-100'}`}>{reemplazos}</p></div>
              <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-500">Sin cambio / vacías</p><p className="text-lg font-bold text-slate-100">{vista.sin_cambio} / {vista.vacias}</p></div>
              <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-500">Errores</p><p className={`text-lg font-bold ${vista.errores.length ? 'text-red-400' : 'text-slate-100'}`}>{vista.errores.length}</p></div>
            </div>

            {vista.errores.length > 0 && (
              <Alert variant="error">
                <p className="font-semibold">Corrige la planilla y vuelve a cargarla. No se aplicará nada mientras tenga errores:</p>
                <ul className="mt-1 list-disc pl-5">
                  {vista.errores.map((e) => <li key={e.fila}>Fila {e.fila}: {e.mensaje}</li>)}
                </ul>
              </Alert>
            )}

            {cambios.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">Cambios por parcela ({cambios.length})</p>
                <ul className="max-h-60 divide-y divide-slate-700/50 overflow-y-auto rounded-lg border border-slate-700 text-sm">
                  {cambios.map((c) => (
                    <li key={c.numero} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 px-3 py-2">
                      <span className="font-medium text-slate-200">Parcela {c.numero}</span>
                      <span className="flex flex-col items-end font-mono text-xs">
                        {c.lectura && (
                          <span className={c.lectura.reemplaza ? 'text-yellow-300' : 'text-slate-300'}>
                            Lectura {c.lectura.antes == null ? '—' : numero(c.lectura.antes)} → <strong className="text-slate-100">{numero(c.lectura.despues)}</strong>
                          </span>
                        )}
                        {c.saldo && (
                          <span className="text-slate-300">
                            Saldo luz {c.saldo.antes == null ? '—' : clp(c.saldo.antes)} → <strong className="text-slate-100">{clp(c.saldo.despues)}</strong>
                          </span>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={cerrar}>Cancelar</Button>
          <Button loading={cargando} disabled={!vista || vista.errores.length > 0 || (vista.a_aplicar.length + vista.saldos.length) === 0} onClick={aplicar}>
            <Upload className="h-4 w-4" /> Aplicar {vista?.a_aplicar.length ?? 0} lecturas{vista?.saldos.length ? ` y ${vista.saldos.length} saldos` : ''}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
