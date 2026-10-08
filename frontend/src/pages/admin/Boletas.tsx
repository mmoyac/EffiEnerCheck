import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Eye, Lock, Calculator, Globe, Trash2, Gauge, FileSpreadsheet } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { boletasApi } from '../../api/boletas'
import { liquidacionesApi } from '../../api/liquidaciones'
import { condominiosApi } from '../../api/condominios'
import { useRole, useAuth } from '../../hooks/useAuth'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { Modal } from '../../components/ui/Modal'
import { Input } from '../../components/ui/Input'
import { Alert } from '../../components/ui/Alert'
import { Spinner } from '../../components/ui/Spinner'
import { clp, kwh, periodoCorto } from '../../utils/format'
import type { BoletaMaestra, SinLecturaAnterior } from '../../types'
import { ImportarLecturasIniciales } from './ImportarLecturasIniciales'

const esLecturaInicial = (b: BoletaMaestra) => b.tipo === 'lectura_inicial'

function EstadoBadge({ b }: { b: BoletaMaestra }) {
  if (esLecturaInicial(b)) {
    return b.lecturas_cerradas ? <Badge color="blue" dot>Cerrada</Badge> : <Badge color="yellow" dot>En toma</Badge>
  }
  if (b.boleta_visible_usuarios) return <Badge color="green" dot>Publicada</Badge>
  if (b.liquidaciones_cerradas)  return <Badge color="blue" dot>Período cerrado</Badge>
  if (b.lecturas_cerradas)       return <Badge color="yellow" dot>Lect. cerradas</Badge>
  if (b.estado === 'validada')   return <Badge color="purple" dot>Corroborada</Badge>
  return <Badge color="slate" dot>Borrador</Badge>
}

const getErrMsg = (e: unknown, defaultMsg: string) => {
  const detail = (e as any)?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => `${d.loc?.[d.loc.length - 1] ?? 'Campo'}: ${d.msg}`).join(' | ');
  }
  if (typeof detail === 'string') return detail;
  return defaultMsg;
};

export default function Boletas() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const role = useRole()
  const { user: me } = useAuth()
  const isSuperAdmin = role === 'super_admin'

  const [modalOpen, setModalOpen] = useState(false)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [filtroCondominio, setFiltroCondominio] = useState('')

  const [form, setForm] = useState({
    condominio_id: '',
  })
  // 409 de la creación: parcelas activas sin lectura anterior (cambio lectura-inicial)
  const [sinLectura, setSinLectura] = useState<SinLecturaAnterior | null>(null)
  // Modal de la lectura inicial: mes de la toma (YYYY-MM)
  const [inicialOpen, setInicialOpen] = useState(false)
  const [mesInicial, setMesInicial] = useState(() => new Date().toISOString().slice(0, 7))
  // Carga desde Excel de la lectura inicial, directo desde la fila
  const [importarDe, setImportarDe] = useState<number | null>(null)

  const { data: boletas = [], isLoading } = useQuery({
    queryKey: ['boletas'],
    queryFn: boletasApi.list,
  })

  const { data: condominios = [] } = useQuery({
    queryKey: ['condominios'],
    queryFn: condominiosApi.list,
    enabled: isSuperAdmin,
  })

  const condominioNombre = (id: number) =>
    condominios.find((c) => c.id === id)?.nombre ?? `#${id}`

  const boletasFiltradas = filtroCondominio
    ? boletas.filter((b) => b.condominio_id === Number(filtroCondominio))
    : boletas

  // La lectura inicial solo se abre en un condominio sin boletas
  const condominioDelForm = form.condominio_id ? Number(form.condominio_id) : me?.condominio_id
  const sinBoletas = (condominioId: number | null | undefined) =>
    !!condominioId && !boletas.some((b) => b.condominio_id === condominioId)
  const puedeLecturaInicial = isSuperAdmin ? sinBoletas(Number(filtroCondominio) || null) : boletas.length === 0

  const createMut = useMutation({
    mutationFn: boletasApi.create,
    onSuccess: (data) => { 
      qc.invalidateQueries({ queryKey: ['boletas'] }); 
      setModalOpen(false); 
      setForm({ condominio_id: '' });
      setSinLectura(null);
      navigate(`/boletas/${data.id}?tab=boleta`);
    },
    onError: (e: unknown) => {
      const detail = (e as any)?.response?.data?.detail
      if (detail?.codigo === 'sin_lectura_anterior') setSinLectura(detail as SinLecturaAnterior)
      else setError(getErrMsg(e, 'Error al crear boleta'))
    },
  })

  const lecturaInicialMut = useMutation({
    mutationFn: boletasApi.crearLecturaInicial,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['boletas'] })
      setInicialOpen(false)
      setModalOpen(false)
      setSinLectura(null)
      navigate(`/boletas/${data.id}?tab=lecturas`)
    },
    onError: (e: unknown) => setError(getErrMsg(e, 'Error al abrir la lectura inicial')),
  })

  const abrirLecturaInicial = (condominioId?: number | null) => {
    setError('')
    if (condominioId) setForm({ condominio_id: String(condominioId) })
    setInicialOpen(true)
  }

  const cerrarLecturasMut = useMutation({
    mutationFn: boletasApi.cerrarLecturas,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['boletas'] }),
  })

  const deleteMut = useMutation({
    mutationFn: boletasApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['boletas'] }),
    onError: (e: unknown) => setActionError(getErrMsg(e, 'Error al eliminar la boleta')),
  })

  const calcularMut = useMutation({
    mutationFn: (id: number) => liquidacionesApi.calcular(id),
    onSuccess: (_data, id) => { qc.invalidateQueries({ queryKey: ['boletas'] }); navigate(`/boletas/${id}?tab=liquidaciones`) },
    onError: (e: unknown) => setActionError(getErrMsg(e, 'Error al calcular liquidaciones')),
  })


  const publicarMut = useMutation({
    mutationFn: (id: number) => boletasApi.update(id, { boleta_visible_usuarios: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['boletas'] }),
  })

  const handleCreate = (aceptar_sin_lectura_anterior = false) => {
    setError('')
    createMut.mutate({
      condominio_id: form.condominio_id ? Number(form.condominio_id) : (me?.condominio_id ?? undefined),
      aceptar_sin_lectura_anterior,
    } as any) // as any porque hicimos los campos opcionales en el backend pero quizas los types.ts todavia piden periodo_mes
  }

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Boletas</h1>
          <p className="text-sm text-slate-500">
            {boletasFiltradas.length}{filtroCondominio ? ` de ${boletas.length}` : ''} períodos registrados
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isSuperAdmin && condominios.length > 0 && (
            <select
              value={filtroCondominio}
              onChange={(e) => setFiltroCondominio(e.target.value)}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-primary-500 focus:outline-none"
            >
              <option value="">Todos los condominios</option>
              {condominios.map((c) => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
          )}
          {puedeLecturaInicial && (
            <Button variant="secondary" onClick={() => abrirLecturaInicial(Number(filtroCondominio) || me?.condominio_id)}>
              <Gauge className="h-4 w-4" /> Comenzar con lectura inicial
            </Button>
          )}
          <Button onClick={() => {
            setForm({ condominio_id: filtroCondominio || (me?.condominio_id ? String(me.condominio_id) : '') })
            setError('')
            setSinLectura(null)
            setModalOpen(true)
          }}>
            <Plus className="h-4 w-4" /> Generar período
          </Button>
        </div>
      </div>

      {actionError && <Alert variant="error">{actionError}</Alert>}

      {puedeLecturaInicial && (
        <Alert variant="info">
          Antes de la primera boleta, registra la <strong>lectura inicial</strong> de cada medidor: es el punto de partida
          del primer consumo. Lo ideal es tomarla el mismo día en que la compañía lee el medidor general.
        </Alert>
      )}

      <Card padding={false}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-5 py-3">Período</th>
                <th className="px-5 py-3">Estado</th>
                {isSuperAdmin && <th className="px-5 py-3">Condominio</th>}
                <th className="px-5 py-3 text-right">kWh</th>
                <th className="px-5 py-3 text-right">Monto neto</th>
                <th className="px-5 py-3 text-right">Total emisión</th>
                <th className="px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {boletasFiltradas.map((b) => (
                <tr key={b.id} className="border-b border-slate-700/50 hover:bg-slate-700/20">
                  <td className="px-5 py-3 font-medium text-slate-200">
                    {esLecturaInicial(b) ? <>Lectura inicial · {periodoCorto(b.periodo_mes)}</> : periodoCorto(b.periodo_mes)}
                  </td>
                  <td className="px-5 py-3"><EstadoBadge b={b} /></td>
                  {isSuperAdmin && <td className="px-5 py-3 text-sm text-slate-400">{condominioNombre(b.condominio_id)}</td>}
                  {esLecturaInicial(b) ? (
                    <td colSpan={3} className="px-5 py-3 text-right text-xs text-slate-500">Sin boleta: solo lecturas de partida</td>
                  ) : (
                    <>
                      <td className="px-5 py-3 text-right font-mono text-slate-300">{kwh(b.total_kwh_compania)}</td>
                      <td className="px-5 py-3 text-right font-mono text-slate-300">{clp(b.monto_neto_electricidad_consumida)}</td>
                      <td className="px-5 py-3 text-right font-mono text-slate-300">{clp(b.monto_total_emision)}</td>
                    </>
                  )}
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Link to={`/boletas/${b.id}`}>
                        <Button variant="ghost" size="sm" title="Ver detalle"><Eye className="h-4 w-4" /></Button>
                      </Link>
                      {esLecturaInicial(b) && !b.lecturas_cerradas && (
                        <Button variant="ghost" size="sm" title="Cargar lecturas iniciales desde Excel" onClick={() => setImportarDe(b.id)}>
                          <FileSpreadsheet className="h-4 w-4 text-primary-400" />
                        </Button>
                      )}
                      {!b.lecturas_cerradas && (
                        <>
                          <Button variant="ghost" size="sm" title="Eliminar boleta"
                            loading={deleteMut.isPending && deleteMut.variables === b.id}
                            onClick={() => { if (window.confirm('¿Seguro que deseas eliminar esta boleta y todos sus datos? Esta acción no se puede deshacer.')) deleteMut.mutate(b.id) }}>
                            <Trash2 className="h-4 w-4 text-red-400 hover:text-red-300" />
                          </Button>
                          <Button variant="ghost" size="sm" title="Cerrar lecturas"
                            loading={cerrarLecturasMut.isPending && cerrarLecturasMut.variables === b.id}
                            onClick={() => cerrarLecturasMut.mutate(b.id)}>
                            <Lock className="h-4 w-4 text-yellow-400 hover:text-yellow-300" />
                          </Button>
                        </>
                      )}
                      {!esLecturaInicial(b) && b.lecturas_cerradas && !b.liquidaciones_cerradas && (
                        <Button variant="ghost" size="sm" title="Calcular liquidaciones"
                          loading={calcularMut.isPending}
                          onClick={() => { setActionError(''); calcularMut.mutate(b.id) }}>
                          <Calculator className="h-4 w-4 text-blue-400" />
                        </Button>
                      )}
                      {!esLecturaInicial(b) && b.liquidaciones_cerradas && !b.boleta_visible_usuarios && (
                        <Button variant="ghost" size="sm" title="Publicar"
                          loading={publicarMut.isPending}
                          onClick={() => publicarMut.mutate(b.id)}>
                          <Globe className="h-4 w-4 text-primary-400" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {boletasFiltradas.length === 0 && (
                <tr><td colSpan={isSuperAdmin ? 7 : 6} className="px-5 py-10 text-center text-slate-500">Sin boletas{filtroCondominio ? ' para este condominio' : ''}.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Generar nuevo período" size="md">
        <div className="space-y-4">
          {error && <Alert variant="error">{error}</Alert>}
          <p className="text-sm text-slate-300">
            El sistema generará el siguiente período mensual automáticamente y copiará las lecturas del mes anterior.
          </p>

          {isSuperAdmin && (
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-slate-300">Condominio</label>
              <select
                value={form.condominio_id}
                onChange={(e) => setForm((f) => ({ ...f, condominio_id: e.target.value }))}
                className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-primary-500 focus:outline-none"
              >
                <option value="">— Seleccionar —</option>
                {condominios.map((c) => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
            </div>
          )}

          {sinLectura ? (
            <div className="space-y-3">
              <Alert variant="warning">
                <strong>{sinLectura.mensaje}.</strong> Su consumo del primer mes sería el número completo del medidor.
              </Alert>
              <p className="text-sm text-slate-400">
                Parcelas: {sinLectura.parcelas.map((p) => p.numero_parcela).join(', ')}
              </p>
              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancelar</Button>
                {sinBoletas(condominioDelForm) && (
                  <Button variant="secondary" onClick={() => abrirLecturaInicial(condominioDelForm)}>
                    <Gauge className="h-4 w-4" /> Comenzar con lectura inicial
                  </Button>
                )}
                <Button variant="danger" loading={createMut.isPending} onClick={() => handleCreate(true)}>
                  Crear igual: ingresaré su lectura anterior
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancelar</Button>
              <Button onClick={() => handleCreate()} loading={createMut.isPending}>Generar</Button>
            </div>
          )}
        </div>
      </Modal>

      {importarDe != null && (
        <ImportarLecturasIniciales open boletaId={importarDe} onClose={() => setImportarDe(null)}
          onAplicada={() => { qc.invalidateQueries({ queryKey: ['boletas'] }); qc.invalidateQueries({ queryKey: ['lecturas', importarDe] }) }} />
      )}

      <Modal open={inicialOpen} onClose={() => setInicialOpen(false)} title="Lectura inicial de los medidores" size="md">
        <div className="space-y-4">
          {error && <Alert variant="error">{error}</Alert>}
          <p className="text-sm text-slate-300">
            Se abre un período especial, sin boleta de la compañía, para registrar la lectura de partida de cada medidor.
            El lector la toma con la app (funciona sin señal y con foto); también puedes ingresarla en la pestaña Lecturas.
            Al cerrar sus lecturas, la primera boleta parte de estos valores.
          </p>
          {isSuperAdmin && (
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-slate-300">Condominio</label>
              <select
                value={form.condominio_id}
                onChange={(e) => setForm((f) => ({ ...f, condominio_id: e.target.value }))}
                className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-primary-500 focus:outline-none"
              >
                <option value="">— Seleccionar —</option>
                {condominios.map((c) => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
            </div>
          )}
          <Input label="Mes en que se toman las lecturas" type="month" value={mesInicial}
                 onChange={(e) => setMesInicial(e.target.value)} />
          <p className="text-xs text-slate-500">La primera boleta quedará en el mes siguiente.</p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setInicialOpen(false)}>Cancelar</Button>
            <Button loading={lecturaInicialMut.isPending} disabled={!mesInicial || (isSuperAdmin && !form.condominio_id)}
                    onClick={() => {
                      setError('')
                      lecturaInicialMut.mutate({
                        condominio_id: form.condominio_id ? Number(form.condominio_id) : (me?.condominio_id ?? undefined),
                        periodo_mes: `${mesInicial}-01`,
                      })
                    }}>
              Abrir lectura inicial
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
