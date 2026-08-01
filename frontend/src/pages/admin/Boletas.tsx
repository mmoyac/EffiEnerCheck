import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Eye, Lock, Calculator, Globe, ScanLine, Camera, Trash2 } from 'lucide-react'
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
import type { BoletaMaestra } from '../../types'

function EstadoBadge({ b }: { b: BoletaMaestra }) {
  if (b.boleta_visible_usuarios) return <Badge color="green" dot>Publicada</Badge>
  if (b.liquidaciones_cerradas)  return <Badge color="blue" dot>Período cerrado</Badge>
  if (b.lecturas_cerradas)       return <Badge color="yellow" dot>Lect. cerradas</Badge>
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

  const createMut = useMutation({
    mutationFn: boletasApi.create,
    onSuccess: (data) => { 
      qc.invalidateQueries({ queryKey: ['boletas'] }); 
      setModalOpen(false); 
      setForm({ condominio_id: '' });
      navigate(`/boletas/${data.id}?tab=boleta`);
    },
    onError: (e: unknown) => setError(getErrMsg(e, 'Error al crear boleta')),
  })

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

  const handleCreate = () => {
    setError('')
    createMut.mutate({
      condominio_id: form.condominio_id ? Number(form.condominio_id) : (me?.condominio_id ?? undefined),
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
          <Button onClick={() => {
            setForm({ condominio_id: filtroCondominio || (me?.condominio_id ? String(me.condominio_id) : '') })
            setModalOpen(true)
          }}>
            <Plus className="h-4 w-4" /> Generar período
          </Button>
        </div>
      </div>

      {actionError && <Alert variant="error">{actionError}</Alert>}

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
                  <td className="px-5 py-3 font-medium text-slate-200">{periodoCorto(b.periodo_mes)}</td>
                  <td className="px-5 py-3"><EstadoBadge b={b} /></td>
                  {isSuperAdmin && <td className="px-5 py-3 text-sm text-slate-400">{condominioNombre(b.condominio_id)}</td>}
                  <td className="px-5 py-3 text-right font-mono text-slate-300">{kwh(b.total_kwh_compania)}</td>
                  <td className="px-5 py-3 text-right font-mono text-slate-300">{clp(b.monto_neto_electricidad_consumida)}</td>
                  <td className="px-5 py-3 text-right font-mono text-slate-300">{clp(b.monto_total_emision)}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Link to={`/boletas/${b.id}`}>
                        <Button variant="ghost" size="sm" title="Ver detalle"><Eye className="h-4 w-4" /></Button>
                      </Link>
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
                      {b.lecturas_cerradas && !b.liquidaciones_cerradas && (
                        <Button variant="ghost" size="sm" title="Calcular liquidaciones"
                          loading={calcularMut.isPending}
                          onClick={() => { setActionError(''); calcularMut.mutate(b.id) }}>
                          <Calculator className="h-4 w-4 text-blue-400" />
                        </Button>
                      )}
                      {b.liquidaciones_cerradas && !b.boleta_visible_usuarios && (
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

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button onClick={handleCreate} loading={createMut.isPending}>Generar</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
