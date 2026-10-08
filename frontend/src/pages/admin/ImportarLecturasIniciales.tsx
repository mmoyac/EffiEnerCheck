import { useState } from 'react'
import type { AxiosError } from 'axios'
import { FileSpreadsheet, Upload } from 'lucide-react'
import { boletasApi } from '../../api/boletas'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Alert'
import { numero } from '../../utils/format'
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

  return (
    <Modal open={open} onClose={cerrar} title="Cargar lecturas iniciales desde Excel" size="xl">
      <div className="space-y-4">
        <p className="text-sm text-slate-300">
          Usa la plantilla (botón «Descargar plantilla»): columnas <strong>Parcela</strong> y <strong>Lectura inicial</strong>.
          Las celdas vacías se omiten. Primero verás una vista previa; nada se guarda hasta que presiones «Aplicar».
        </p>

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
              <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-500">A aplicar</p><p className="text-lg font-bold text-slate-100">{vista.a_aplicar.length}</p></div>
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

            {vista.a_aplicar.length > 0 && (
              <div className="max-h-64 overflow-y-auto rounded-lg border border-slate-700">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-slate-800">
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                      <th className="px-4 py-2">Parcela</th>
                      <th className="px-4 py-2 text-right">Actual</th>
                      <th className="px-4 py-2 text-right">Nueva</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vista.a_aplicar.map((f) => (
                      <tr key={f.lectura_id} className="border-t border-slate-700/50">
                        <td className="px-4 py-2 text-slate-200">{f.numero_parcela}</td>
                        <td className={`px-4 py-2 text-right font-mono ${f.reemplaza ? 'text-yellow-300' : 'text-slate-500'}`}>
                          {f.valor_actual == null ? '—' : numero(f.valor_actual)}
                        </td>
                        <td className="px-4 py-2 text-right font-mono text-slate-100">{numero(f.valor)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={cerrar}>Cancelar</Button>
          <Button loading={cargando} disabled={!vista || vista.errores.length > 0 || vista.a_aplicar.length === 0} onClick={aplicar}>
            <Upload className="h-4 w-4" /> Aplicar {vista?.a_aplicar.length ?? 0} lecturas
          </Button>
        </div>
      </div>
    </Modal>
  )
}
