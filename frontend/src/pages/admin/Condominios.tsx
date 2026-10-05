import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, Plus, Pencil, Check, X, Upload, Trash2, AlertTriangle } from 'lucide-react'
import {
  condominiosApi, type Condominio, type CondominioCreate, type PlanSuscripcion,
} from '../../api/condominios'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Badge } from '../../components/ui/Badge'
import { Spinner } from '../../components/ui/Spinner'
import { Alert } from '../../components/ui/Alert'
import { ETIQUETA_MODULO, MODULOS, type Modulo } from '../../config/modulos'
import { PLATAFORMA } from '../../config/marca'
import { bajoContraste, escalaDesde, textoSobre } from '../../utils/color'

type ErrorApi = { response?: { data?: { detail?: string | { msg: string }[] } } }

function mensajeError(e: unknown, porDefecto: string): string {
  const detail = (e as ErrorApi)?.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg.replace(/^Value error, /, '')).join(' · ')
  return detail ?? porDefecto
}

/** "Solo administración", "Solo landing", "Landing + administración" o "Sin productos" */
export function resumenContratacion(modulos: Modulo[]): string {
  const landing = modulos.includes('sitio')
  const portal = modulos.includes('portal')
  if (landing && portal) return 'Landing + administración'
  if (portal) return 'Solo administración'
  if (landing) return 'Solo landing'
  return 'Sin productos'
}

const rgb = (v: number[]) => `rgb(${v.map(Math.round).join(',')})`

function VistaPreviaColor({ color }: { color: string }) {
  const escala = escalaDesde(color)
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 p-3">
      <span className="rounded-lg px-3 py-1.5 text-sm font-medium" style={{ background: rgb(escala[600]), color: '#fff' }}>
        Botón
      </span>
      <span className="rounded-lg px-3 py-1.5 text-sm font-medium" style={{ background: `${rgb(escala[600])}33`, color: rgb(escala[400]) }}>
        Menú activo
      </span>
      <span className="rounded-lg px-3 py-1.5 text-sm font-semibold" style={{ background: color, color: textoSobre(color) }}>
        Acceso propietarios
      </span>
    </div>
  )
}

function Contratacion({
  modulos, setModulos, portalUrl, setPortalUrl, dominios, setDominios, color, setColor,
}: {
  modulos: Modulo[]; setModulos: (m: Modulo[]) => void
  portalUrl: string; setPortalUrl: (v: string) => void
  dominios: string; setDominios: (v: string) => void
  color: string | null; setColor: (v: string | null) => void
}) {
  const tiene = (m: Modulo) => modulos.includes(m)
  const alternar = (m: Modulo) => {
    let nuevos = tiene(m) ? modulos.filter((x) => x !== m) : [...modulos, m]
    // Energía y Rifas viven dentro del portal: sin Administración no pueden quedar marcados
    if (m === 'portal' && tiene('portal')) nuevos = nuevos.filter((x) => x !== 'energia' && x !== 'rifas')
    setModulos(MODULOS.filter((x) => nuevos.includes(x)))
  }
  const casilla = (m: Modulo, descripcion: string, deshabilitada = false) => (
    <label className={`flex items-start gap-2 text-sm ${deshabilitada ? 'opacity-40' : ''}`}>
      <input type="checkbox" checked={tiene(m)} disabled={deshabilitada} onChange={() => alternar(m)}
        className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-800 accent-primary-600" />
      <span>
        <span className="font-medium text-slate-200">{ETIQUETA_MODULO[m]}</span>
        <span className="block text-xs text-slate-500">{descripcion}</span>
      </span>
    </label>
  )

  return (
    <div className="space-y-4 rounded-lg border border-slate-700 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-300">Contratación</p>
        <Badge color="blue">{resumenContratacion(modulos)}</Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Productos</p>
          {casilla('sitio', 'Sitio web público del condominio')}
          {casilla('portal', 'Portal con login para la comunidad')}
        </div>
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Módulos de administración</p>
          {casilla('energia', `${PLATAFORMA.modulos.energia}: boletas, lecturas y liquidaciones`, !tiene('portal'))}
          {casilla('rifas', 'Rifas solidarias y venta en portería', !tiene('portal'))}
        </div>
      </div>

      <Input label="URL del portal" value={portalUrl} onChange={(e) => setPortalUrl(e.target.value)}
        placeholder="https://portal.micondominio.cl" />
      <p className="-mt-2 text-xs text-slate-500">
        Destino del botón "Acceso propietarios" de la landing. Un condominio con web propia también puede enlazarla.
      </p>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-slate-300">Dominios de la landing</label>
        <textarea value={dominios} onChange={(e) => setDominios(e.target.value)} rows={2}
          placeholder={'micondominio.cl'}
          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-primary-500 focus:outline-none" />
        <p className="text-xs text-slate-500">Uno por línea. Con o sin www (se reconocen igual).</p>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium text-slate-300">Color institucional</label>
          <input type="color" value={color ?? PLATAFORMA.colorPorDefecto} onChange={(e) => setColor(e.target.value.toUpperCase())}
            className="h-8 w-12 cursor-pointer rounded border border-slate-600 bg-slate-800" />
          <span className="font-mono text-xs text-slate-400">{color ?? 'Por defecto'}</span>
          {color && (
            <button type="button" onClick={() => setColor(null)} className="text-xs text-slate-400 underline hover:text-slate-200">
              Usar el color por defecto
            </button>
          )}
        </div>
        <VistaPreviaColor color={color ?? PLATAFORMA.colorPorDefecto} />
        {color && bajoContraste(color) && (
          <p className="flex items-center gap-1.5 text-xs text-yellow-400">
            <AlertTriangle className="h-3.5 w-3.5" />
            Color claro: en el portal, los botones usarán un tono más oscuro que el elegido para que el texto se lea.
          </p>
        )}
      </div>
    </div>
  )
}

function LogoCondominio({ condominio }: { condominio: Condominio }) {
  const qc = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [error, setError] = useState('')
  const listo = () => { qc.invalidateQueries({ queryKey: ['condominios'] }); setError('') }

  const subir = useMutation({
    mutationFn: (archivo: File) => condominiosApi.subirLogo(condominio.id, archivo),
    onSuccess: listo,
    onError: (e) => setError(mensajeError(e, 'No se pudo subir el logo')),
  })
  const quitar = useMutation({
    mutationFn: () => condominiosApi.quitarLogo(condominio.id),
    onSuccess: listo,
    onError: (e) => setError(mensajeError(e, 'No se pudo quitar el logo')),
  })

  return (
    <div className="space-y-2 rounded-lg border border-slate-700 p-4">
      <p className="text-sm font-semibold text-slate-300">Logo</p>
      <div className="flex items-center gap-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-white p-1">
          {condominio.logo_url
            ? <img src={condominio.logo_url} alt={`Logo de ${condominio.nombre}`} className="max-h-full max-w-full object-contain" />
            : <Building2 className="h-6 w-6 text-slate-400" />}
        </div>
        <div className="flex flex-wrap gap-2">
          <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) subir.mutate(f); e.target.value = '' }} />
          <Button type="button" size="sm" variant="ghost" loading={subir.isPending} onClick={() => input.current?.click()}>
            <Upload className="h-4 w-4" /> {condominio.logo_url ? 'Reemplazar' : 'Subir'}
          </Button>
          {condominio.logo_url && (
            <Button type="button" size="sm" variant="ghost" loading={quitar.isPending}
              onClick={() => { if (confirm('¿Quitar el logo del condominio?')) quitar.mutate() }}>
              <Trash2 className="h-4 w-4" /> Quitar
            </Button>
          )}
        </div>
      </div>
      <p className="text-xs text-slate-500">PNG, JPEG o WEBP de hasta 1 MB. Se muestra en la landing y en el portal.</p>
      {error && <Alert variant="error">{error}</Alert>}
    </div>
  )
}

function CondominioForm({
  initial,
  onSave,
  onCancel,
  loading,
}: {
  initial?: Condominio
  onSave: (data: CondominioCreate) => void
  onCancel: () => void
  loading: boolean
}) {
  const [nombre, setNombre] = useState(initial?.nombre ?? '')
  const [rut, setRut] = useState(initial?.rut_comunidad ?? '')
  const [direccion, setDireccion] = useState(initial?.direccion ?? '')
  const [plan, setPlan] = useState<PlanSuscripcion>(initial?.plan_suscripcion ?? 'basico')
  const [modulos, setModulos] = useState<Modulo[]>(initial?.modulos ?? [...MODULOS])
  const [portalUrl, setPortalUrl] = useState(initial?.portal_url ?? '')
  const [dominios, setDominios] = useState((initial?.dominios_sitio ?? []).join('\n'))
  const [color, setColor] = useState<string | null>(initial?.color_primario ?? null)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const quitados = (initial?.modulos ?? []).filter((m) => !modulos.includes(m))
    if (quitados.length > 0 && !confirm(
      `Vas a quitar: ${quitados.map((m) => ETIQUETA_MODULO[m]).join(', ')}. ` +
      'Los datos no se borran, pero dejarán de estar disponibles para el condominio. ¿Continuar?',
    )) return
    onSave({
      nombre,
      rut_comunidad: rut,
      direccion: direccion || undefined,
      plan_suscripcion: plan,
      modulos,
      portal_url: portalUrl.trim() || null,
      dominios_sitio: dominios.split(/[\n,]/).map((d) => d.trim()).filter(Boolean),
      color_primario: color,
    })
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <Input label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
      <Input label="RUT comunidad" value={rut} onChange={(e) => setRut(e.target.value)} placeholder="12.345.678-9"
        required disabled={!!initial} />
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
      <Contratacion
        modulos={modulos} setModulos={setModulos}
        portalUrl={portalUrl} setPortalUrl={setPortalUrl}
        dominios={dominios} setDominios={setDominios}
        color={color} setColor={setColor}
      />
      {initial && <LogoCondominio condominio={initial} />}
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
    onError: (e: unknown) => setError(mensajeError(e, 'Error al crear')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: CondominioCreate }) => {
      const { rut_comunidad: _rut, ...cambios } = data
      return condominiosApi.update(id, cambios)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['condominios'] }); setEditId(null); setError('') },
    onError: (e: unknown) => setError(mensajeError(e, 'Error al actualizar')),
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
                  initial={c}
                  onSave={(d) => updateMutation.mutate({ id: c.id, data: d })}
                  onCancel={() => { setEditId(null); setError('') }}
                  loading={updateMutation.isPending}
                />
              </>
            ) : (
              <div className="flex items-start justify-between gap-4">
                <div className="flex min-w-0 items-start gap-3">
                  {c.logo_url ? (
                    <img src={c.logo_url} alt="" className="mt-0.5 h-10 w-10 flex-shrink-0 rounded-lg bg-white object-contain p-0.5" />
                  ) : (
                    <div className="mt-0.5 rounded-lg bg-primary-600/15 p-2">
                      <Building2 className="h-5 w-5 text-primary-400" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="flex items-center gap-2 font-semibold text-slate-100">
                      {c.color_primario && (
                        <span className="inline-block h-3 w-3 rounded-full" style={{ background: c.color_primario }} title={c.color_primario} />
                      )}
                      {c.nombre}
                    </p>
                    <p className="text-sm text-slate-400">{c.rut_comunidad}</p>
                    {c.direccion && <p className="text-xs text-slate-500 mt-0.5">{c.direccion}</p>}
                    <p className="text-xs text-slate-600 mt-0.5 capitalize">Plan {c.plan_suscripcion}</p>
                    <p className="mt-1.5 text-xs text-slate-400">
                      {resumenContratacion(c.modulos)}
                      {c.modulos.includes('portal') && (
                        <> · {(['energia', 'rifas'] as Modulo[]).filter((m) => c.modulos.includes(m)).map((m) => ETIQUETA_MODULO[m]).join(', ') || 'solo núcleo'}</>
                      )}
                    </p>
                    {c.dominios_sitio.length > 0 && (
                      <p className="truncate text-xs text-slate-500">Landing: {c.dominios_sitio.join(', ')}</p>
                    )}
                    {c.portal_url && <p className="truncate text-xs text-slate-500">Portal: {c.portal_url}</p>}
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
