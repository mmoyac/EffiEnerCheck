import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MapPin, Plus, Pencil, X, Check, Route } from 'lucide-react'
import { parcelasApi } from '../../api/parcelas'
import { condominiosApi } from '../../api/condominios'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Alert } from '../../components/ui/Alert'
import { Spinner } from '../../components/ui/Spinner'
import { useRole, useAuth } from '../../hooks/useAuth'
import type { Parcela } from '../../types'
import { OrdenRecorridoModal } from './OrdenRecorridoModal'

interface ParcelaForm {
  numero_parcela: string
  propietario_nombre: string
  condominio_id: string
  activa: boolean
}

const EMPTY: ParcelaForm = { numero_parcela: '', propietario_nombre: '', condominio_id: '', activa: true }

const SELECT_CLS = 'w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-primary-500 focus:outline-none'

interface InlineFormProps {
  value: ParcelaForm
  condominios: { id: number; nombre: string }[]
  isSuperAdmin: boolean
  onSave: (f: ParcelaForm) => void
  onCancel: () => void
  loading: boolean
  error: string
  // 'fila': <tr> de la tabla (escritorio); 'tarjeta': <li> apilado (celular)
  variante?: 'fila' | 'tarjeta'
}

function InlineForm({
  value,
  condominios,
  isSuperAdmin,
  onSave,
  onCancel,
  loading,
  error,
  variante = 'fila',
}: InlineFormProps) {
  const [form, setForm] = useState(value)
  const set = (patch: Partial<ParcelaForm>) => setForm((f) => ({ ...f, ...patch }))

  // Mismos campos para ambas variantes
  const numero = (
    <Input
      value={form.numero_parcela}
      onChange={(e) => set({ numero_parcela: e.target.value })}
      placeholder="Ej: 23"
      required
    />
  )
  const propietario = (
    <Input
      value={form.propietario_nombre}
      onChange={(e) => set({ propietario_nombre: e.target.value })}
      placeholder="Nombre propietario"
    />
  )
  const condominio = (
    <select
      value={form.condominio_id}
      onChange={(e) => set({ condominio_id: e.target.value })}
      className={SELECT_CLS}
    >
      <option value="">— Condominio —</option>
      {condominios.map((c) => (
        <option key={c.id} value={c.id}>{c.nombre}</option>
      ))}
    </select>
  )
  const estado = (
    <select
      value={form.activa ? '1' : '0'}
      onChange={(e) => set({ activa: e.target.value === '1' })}
      className={SELECT_CLS}
    >
      <option value="1">Activa</option>
      <option value="0">Inactiva</option>
    </select>
  )
  const acciones = (
    <>
      <Button size="sm" variant="ghost" onClick={onCancel} disabled={loading}>
        <X className="h-4 w-4" />
      </Button>
      <Button size="sm" loading={loading} onClick={() => onSave(form)}>
        <Check className="h-4 w-4" />
      </Button>
    </>
  )

  if (variante === 'tarjeta') {
    return (
      <li className="space-y-2 bg-slate-800/60 px-4 py-3">
        {numero}
        {propietario}
        {isSuperAdmin && condominio}
        {estado}
        {error && <p className="text-xs text-red-400">{error}</p>}
        <div className="flex justify-end gap-1">{acciones}</div>
      </li>
    )
  }

  return (
    <tr className="border-b border-slate-700 bg-slate-800/60">
      <td className="px-4 py-2">{numero}</td>
      <td className="px-4 py-2">{propietario}</td>
      {isSuperAdmin && <td className="px-4 py-2">{condominio}</td>}
      <td className="px-4 py-2">{estado}</td>
      <td className="px-4 py-2">
        <div className="flex items-center gap-1">
          {error && <span className="mr-2 text-xs text-red-400">{error}</span>}
          {acciones}
        </div>
      </td>
    </tr>
  )
}

export default function Parcelas() {
  const qc = useQueryClient()
  const role = useRole()
  const { user: me } = useAuth()
  const isSuperAdmin = role === 'super_admin'

  const [filtroCondominio, setFiltroCondominio] = useState('')
  const [addingNew, setAddingNew] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [recorridoOpen, setRecorridoOpen] = useState(false)

  const { data: parcelas = [], isLoading } = useQuery({ queryKey: ['parcelas'], queryFn: parcelasApi.list })
  const { data: condominios = [] } = useQuery({ queryKey: ['condominios'], queryFn: condominiosApi.list, enabled: isSuperAdmin })

  const parcelasFiltradas = (filtroCondominio
    ? parcelas.filter((p) => p.condominio_id === Number(filtroCondominio))
    : parcelas
  ).slice().sort((a, b) =>
    a.numero_parcela.localeCompare(b.numero_parcela, undefined, { numeric: true, sensitivity: 'base' })
  )

  const condominioNombre = (id: number) =>
    condominios.find((c) => c.id === id)?.nombre ?? `#${id}`

  const defaultCondominioId = filtroCondominio || (me?.condominio_id ? String(me.condominio_id) : '')

  const createMut = useMutation({
    mutationFn: (f: ParcelaForm) => parcelasApi.create({
      numero_parcela: f.numero_parcela,
      propietario_nombre: f.propietario_nombre || undefined,
      condominio_id: Number(f.condominio_id) || me?.condominio_id!,
      activa: f.activa,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['parcelas'] }); setAddingNew(false); setError('') },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al crear'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, f }: { id: number; f: ParcelaForm }) => parcelasApi.update(id, {
      numero_parcela: f.numero_parcela,
      propietario_nombre: f.propietario_nombre || undefined,
      activa: f.activa,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['parcelas'] }); setEditId(null); setError('') },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al actualizar'),
  })

  if (isLoading) return <div className="flex h-64 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>

  const colSpan = isSuperAdmin ? 5 : 4

  // Props del formulario en línea, compartidas por la tabla y la lista del celular
  const formNuevaProps = {
    value: { ...EMPTY, condominio_id: defaultCondominioId },
    condominios,
    isSuperAdmin,
    onSave: (f: ParcelaForm) => createMut.mutate(f),
    onCancel: () => { setAddingNew(false); setError('') },
    loading: createMut.isPending,
    error: addingNew ? error : '',
  }
  const formEdicionProps = (p: Parcela) => ({
    value: {
      numero_parcela: p.numero_parcela,
      propietario_nombre: p.propietario_nombre ?? '',
      condominio_id: String(p.condominio_id),
      activa: p.activa,
    },
    condominios,
    isSuperAdmin,
    onSave: (f: ParcelaForm) => updateMut.mutate({ id: p.id, f }),
    onCancel: () => { setEditId(null); setError('') },
    loading: updateMut.isPending,
    error: editId === p.id ? error : '',
  })
  const editar = (p: Parcela) => { setEditId(p.id); setError('') }
  const estadoBadge = (p: Parcela) => p.activa
    ? <Badge color="green" dot>Activa</Badge>
    : <Badge color="red" dot>Inactiva</Badge>
  const textoVacio = `Sin parcelas${filtroCondominio ? ' en este condominio' : ''}`

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-slate-100">Parcelas</h1>
          <p className="text-sm text-slate-500">
            {parcelasFiltradas.filter((p) => p.activa).length} activas de {parcelasFiltradas.length}
            {filtroCondominio ? ` (total: ${parcelas.length})` : ''}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {isSuperAdmin && condominios.length > 0 && (
            <select
              value={filtroCondominio}
              onChange={(e) => setFiltroCondominio(e.target.value)}
              className="min-w-0 max-w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-primary-500 focus:outline-none"
            >
              <option value="">Todos los condominios</option>
              {condominios.map((c) => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
          )}
          <Button size="sm" variant="secondary" disabled={isSuperAdmin && !filtroCondominio}
                  title={isSuperAdmin && !filtroCondominio ? 'Elige primero un condominio' : 'Orden en que el lector camina las parcelas'}
                  onClick={() => setRecorridoOpen(true)}>
            <Route className="h-4 w-4" /> Orden del recorrido
          </Button>
          <OrdenRecorridoModal
            open={recorridoOpen}
            condominioId={isSuperAdmin ? Number(filtroCondominio) || null : null}
            parcelas={isSuperAdmin ? parcelas.filter((p) => p.condominio_id === Number(filtroCondominio)) : parcelas}
            onClose={() => setRecorridoOpen(false)}
            onGuardado={() => qc.invalidateQueries({ queryKey: ['parcelas'] })}
          />
          {!addingNew && (
            <Button size="sm" onClick={() => { setAddingNew(true); setError('') }}>
              <Plus className="h-4 w-4" /> Nueva parcela
            </Button>
          )}
        </div>
      </div>

      {error && !addingNew && !editId && <Alert variant="error">{error}</Alert>}

      <Card padding={false}>
        {/* Escritorio: tabla */}
        <div className="hidden overflow-x-auto md:block">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-5 py-3">N° Parcela</th>
                <th className="px-5 py-3">Propietario</th>
                {isSuperAdmin && <th className="px-5 py-3">Condominio</th>}
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3 w-24"></th>
              </tr>
            </thead>
            <tbody>
              {addingNew && <InlineForm {...formNuevaProps} />}

              {parcelasFiltradas.map((p: Parcela) =>
                editId === p.id ? (
                  <InlineForm key={p.id} {...formEdicionProps(p)} />
                ) : (
                  <tr key={p.id} className="border-b border-slate-700/50 hover:bg-slate-700/20">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-slate-500" />
                        <span className="font-medium text-slate-200">Parcela {p.numero_parcela}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-slate-400">{p.propietario_nombre ?? '—'}</td>
                    {isSuperAdmin && (
                      <td className="px-5 py-3 text-slate-400 text-sm">{condominioNombre(p.condominio_id)}</td>
                    )}
                    <td className="px-5 py-3">{estadoBadge(p)}</td>
                    <td className="px-5 py-3">
                      <Button size="sm" variant="ghost" onClick={() => editar(p)}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                )
              )}

              {parcelasFiltradas.length === 0 && !addingNew && (
                <tr>
                  <td colSpan={colSpan} className="px-5 py-8 text-center text-slate-500">{textoVacio}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Celular: lista apilada, una tarjeta por parcela */}
        <ul className="divide-y divide-slate-700/50 md:hidden">
          {addingNew && <InlineForm {...formNuevaProps} variante="tarjeta" />}

          {parcelasFiltradas.map((p: Parcela) =>
            editId === p.id ? (
              <InlineForm key={p.id} {...formEdicionProps(p)} variante="tarjeta" />
            ) : (
              <li key={p.id} className="flex items-center gap-3 px-4 py-3 text-sm">
                <MapPin className="h-4 w-4 shrink-0 text-slate-500" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-slate-200">Parcela {p.numero_parcela}</p>
                  <p className="truncate text-slate-400">{p.propietario_nombre ?? '—'}</p>
                  {isSuperAdmin && (
                    <p className="truncate text-xs text-slate-500">{condominioNombre(p.condominio_id)}</p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  {estadoBadge(p)}
                  <Button size="sm" variant="ghost" onClick={() => editar(p)}>
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </li>
            )
          )}

          {parcelasFiltradas.length === 0 && !addingNew && (
            <li className="px-4 py-8 text-center text-sm text-slate-500">{textoVacio}</li>
          )}
        </ul>
      </Card>
    </div>
  )
}
