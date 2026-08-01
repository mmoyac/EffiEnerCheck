import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, Plus, Pencil, Check, X } from 'lucide-react'
import { condominiosApi, type Condominio, type CondominioCreate, type PlanSuscripcion } from '../../api/condominios'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Badge } from '../../components/ui/Badge'
import { Spinner } from '../../components/ui/Spinner'
import { Alert } from '../../components/ui/Alert'

function CondominioForm({
  initial,
  onSave,
  onCancel,
  loading,
}: {
  initial?: Partial<CondominioCreate>
  onSave: (data: CondominioCreate) => void
  onCancel: () => void
  loading: boolean
}) {
  const [nombre, setNombre] = useState(initial?.nombre ?? '')
  const [rut, setRut] = useState(initial?.rut_comunidad ?? '')
  const [direccion, setDireccion] = useState(initial?.direccion ?? '')
  const [plan, setPlan] = useState<PlanSuscripcion>(initial?.plan_suscripcion ?? 'basico')

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({ nombre, rut_comunidad: rut, direccion: direccion || undefined, plan_suscripcion: plan })
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <Input label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
      <Input label="RUT comunidad" value={rut} onChange={(e) => setRut(e.target.value)} placeholder="12.345.678-9" required />
      <Input label="Dirección" value={direccion} onChange={(e) => setDireccion(e.target.value)} />
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-slate-300">Plan</label>
        <select value={plan} onChange={(e) => setPlan(e.target.value as PlanSuscripcion)}
          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-primary-500 focus:outline-none">
          <option value="basico">Básico</option>
          <option value="pro">Pro</option>
          <option value="premium">Premium</option>
        </select>
      </div>
      <div className="flex justify-end gap-2 pt-1">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={loading}>
          <X className="h-4 w-4" /> Cancelar
        </Button>
        <Button type="submit" size="sm" loading={loading}>
          <Check className="h-4 w-4" /> Guardar
        </Button>
      </div>
    </form>
  )
}

export default function Condominios() {
  const qc = useQueryClient()
  const [showNew, setShowNew] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [error, setError] = useState('')

  const { data: condominios = [], isLoading } = useQuery({
    queryKey: ['condominios'],
    queryFn: condominiosApi.list,
  })

  const createMutation = useMutation({
    mutationFn: condominiosApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['condominios'] }); setShowNew(false); setError('') },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al crear'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CondominioCreate> }) => condominiosApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['condominios'] }); setEditId(null); setError('') },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al actualizar'),
  })

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Condominios</h1>
          <p className="text-sm text-slate-500">{condominios.length} registrados</p>
        </div>
        {!showNew && (
          <Button size="sm" onClick={() => setShowNew(true)}>
            <Plus className="h-4 w-4" /> Nuevo
          </Button>
        )}
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {showNew && (
        <Card>
          <p className="mb-4 text-sm font-semibold text-slate-300">Nuevo condominio</p>
          <CondominioForm
            onSave={(d) => createMutation.mutate(d)}
            onCancel={() => { setShowNew(false); setError('') }}
            loading={createMutation.isPending}
          />
        </Card>
      )}

      <div className="space-y-3">
        {condominios.map((c: Condominio) => (
          <Card key={c.id}>
            {editId === c.id ? (
              <>
                <p className="mb-4 text-sm font-semibold text-slate-300">Editar condominio</p>
                <CondominioForm
                  initial={{ nombre: c.nombre, rut_comunidad: c.rut_comunidad, direccion: c.direccion ?? '', plan_suscripcion: c.plan_suscripcion }}
                  onSave={(d) => updateMutation.mutate({ id: c.id, data: d })}
                  onCancel={() => { setEditId(null); setError('') }}
                  loading={updateMutation.isPending}
                />
              </>
            ) : (
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 rounded-lg bg-primary-600/15 p-2">
                    <Building2 className="h-5 w-5 text-primary-400" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-100">{c.nombre}</p>
                    <p className="text-sm text-slate-400">{c.rut_comunidad}</p>
                    {c.direccion && <p className="text-xs text-slate-500 mt-0.5">{c.direccion}</p>}
                    <p className="text-xs text-slate-600 mt-0.5 capitalize">Plan {c.plan_suscripcion}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge color={c.activo ? 'green' : 'slate'}>{c.activo ? 'Activo' : 'Inactivo'}</Badge>
                  <Button size="sm" variant="ghost" onClick={() => setEditId(c.id)}>
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        ))}

        {condominios.length === 0 && !showNew && (
          <Card>
            <p className="py-8 text-center text-slate-500">No hay condominios registrados</p>
          </Card>
        )}
      </div>
    </div>
  )
}
