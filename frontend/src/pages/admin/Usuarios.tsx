import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, UserCircle, Pencil, Send, MessageCircle, Copy, Check, Mail } from 'lucide-react'
import { usuariosApi } from '../../api/usuarios'
import { parcelasApi } from '../../api/parcelas'
import { condominiosApi } from '../../api/condominios'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { Modal } from '../../components/ui/Modal'
import { Input } from '../../components/ui/Input'
import { Alert } from '../../components/ui/Alert'
import { Spinner } from '../../components/ui/Spinner'
import { fecha } from '../../utils/format'
import { formatearTelefono, normalizarTelefono } from '../../utils/telefono'
import { useAuth, useRole } from '../../hooks/useAuth'
import { mensajeInvitacion, urlWhatsApp } from '../../utils/whatsapp'
import type { Invitacion, Usuario } from '../../types'
import type { Condominio } from '../../api/condominios'

const ROLE_COLOR: Record<string, 'purple' | 'blue' | 'yellow' | 'green'> = {
  super_admin:      'purple',
  admin_condominio: 'blue',
  lector:           'yellow',
  parcelero:        'green',
  porteria:         'yellow',
}

const ROLES = [
  { id: 1, nombre: 'super_admin' },
  { id: 2, nombre: 'admin_condominio' },
  { id: 3, nombre: 'lector' },
  { id: 4, nombre: 'parcelero' },
  { id: 5, nombre: 'porteria' },
]

interface FormState {
  nombre: string
  email: string
  telefono: string
  password: string
  rol_id: string
  condominio_id: string
  parcela_ids: number[]
}

const EMPTY_FORM: FormState = {
  nombre: '', email: '', telefono: '', password: '', rol_id: '2', condominio_id: '', parcela_ids: [],
}

function UsuarioForm({
  form,
  onChange,
  condominios,
  parcelas,
  isSuperAdmin,
  isEdit,
}: {
  form: FormState
  onChange: (patch: Partial<FormState>) => void
  condominios: Condominio[]
  parcelas: { id: number; condominio_id: number; numero_parcela: string; propietario_nombre: string | null }[]
  isSuperAdmin: boolean
  isEdit: boolean
}) {
  const parcelasFiltradas = form.condominio_id
    ? parcelas.filter((p) => p.condominio_id === Number(form.condominio_id))
    : parcelas

  return (
    <div className="space-y-4">
      <Input
        label="Nombre completo"
        value={form.nombre}
        onChange={(e) => onChange({ nombre: e.target.value })}
        required
      />
      <Input
        label="Correo electrónico"
        type="email"
        value={form.email}
        onChange={(e) => onChange({ email: e.target.value })}
        required
      />
      <Input
        label="Teléfono (opcional)"
        type="tel"
        inputMode="tel"
        value={form.telefono}
        onChange={(e) => onChange({ telefono: e.target.value })}
        placeholder="Ej: 9 1234 5678"
        error={normalizarTelefono(form.telefono) === undefined ? 'Debe tener 8 o 9 dígitos, o empezar con 56' : undefined}
        hint="Se usa para enviar comprobantes por WhatsApp"
      />
      <Input
        label={isEdit ? 'Nueva contraseña (opcional)' : 'Contraseña (opcional)'}
        type="password"
        value={form.password}
        onChange={(e) => onChange({ password: e.target.value })}
        autoComplete="new-password"
        hint={isEdit
          ? 'Déjala vacía para no cambiarla. Mejor: que la persona use «¿Olvidaste tu clave?»'
          : 'Déjala vacía y envía una invitación: la persona creará su propia clave (mín. 10 caracteres)'}
      />

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-slate-300">Rol</label>
          <select
            value={form.rol_id}
            onChange={(e) => onChange({ rol_id: e.target.value, parcela_ids: [] })}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-primary-500 focus:outline-none"
          >
            {ROLES.map((r) => (
              <option key={r.id} value={r.id}>{r.nombre}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-slate-300">Condominio</label>
          {isSuperAdmin ? (
            <select
              value={form.condominio_id}
              onChange={(e) => onChange({ condominio_id: e.target.value, parcela_ids: [] })}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-primary-500 focus:outline-none"
            >
              <option value="">— Sin condominio —</option>
              {condominios.map((c) => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
          ) : (
            <input
              disabled
              value={condominios.find((c) => c.id === Number(form.condominio_id))?.nombre ?? '—'}
              className="rounded-lg border border-slate-700 bg-slate-700/40 px-3 py-2 text-slate-400 cursor-not-allowed"
            />
          )}
        </div>
      </div>

      {form.rol_id === '4' && (
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-slate-300">Parcelas asignadas</label>
          <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-600 bg-slate-800 p-2 space-y-1">
            {parcelasFiltradas.length === 0 && (
              <p className="px-2 py-2 text-sm text-slate-500">
                {form.condominio_id ? 'Sin parcelas en este condominio' : 'Selecciona un condominio primero'}
              </p>
            )}
            {parcelasFiltradas.map((p) => (
              <label key={p.id} className="flex items-center gap-2 rounded px-2 py-1 hover:bg-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.parcela_ids.includes(p.id)}
                  onChange={(e) => onChange({
                    parcela_ids: e.target.checked
                      ? [...form.parcela_ids, p.id]
                      : form.parcela_ids.filter((id) => id !== p.id),
                  })}
                  className="accent-primary-500"
                />
                <span className="text-sm text-slate-300">Parcela {p.numero_parcela}</span>
                {p.propietario_nombre && <span className="text-xs text-slate-500">— {p.propietario_nombre}</span>}
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Usuarios() {
  const qc = useQueryClient()
  const { user: me } = useAuth()
  const role = useRole()
  const isSuperAdmin = role === 'super_admin'

  const [createOpen, setCreateOpen] = useState(false)
  const [editUser, setEditUser] = useState<Usuario | null>(null)
  const [createForm, setCreateForm] = useState<FormState>(EMPTY_FORM)
  const [editForm, setEditForm] = useState<FormState>(EMPTY_FORM)
  const [error, setError] = useState('')
  const [filtroCondominio, setFiltroCondominio] = useState<string>('')
  const [invitacion, setInvitacion] = useState<{ usuario: Usuario; resultado: Invitacion } | null>(null)
  const [aviso, setAviso] = useState<{ variante: 'success' | 'error'; texto: string } | null>(null)

  const { data: usuarios = [], isLoading } = useQuery({ queryKey: ['usuarios'], queryFn: usuariosApi.list })
  const { data: parcelas = [] } = useQuery({ queryKey: ['parcelas'], queryFn: parcelasApi.list })
  const { data: condominios = [] } = useQuery({ queryKey: ['condominios'], queryFn: condominiosApi.list })

  const condominioNombre = (id: number | null) =>
    id ? (condominios.find((c) => c.id === id)?.nombre ?? `#${id}`) : '—'

  const usuariosFiltrados = filtroCondominio === ''
    ? usuarios
    : filtroCondominio === 'sin'
      ? usuarios.filter((u) => u.condominio_id === null)
      : usuarios.filter((u) => u.condominio_id === Number(filtroCondominio))

  const createMut = useMutation({
    mutationFn: usuariosApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['usuarios'] })
      setCreateOpen(false)
      setCreateForm(EMPTY_FORM)
      setError('')
    },
    onError: (e: unknown) =>
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al crear usuario'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: object }) => usuariosApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['usuarios'] })
      setEditUser(null)
      setError('')
    },
    onError: (e: unknown) =>
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al actualizar'),
  })

  const errorDe = (e: unknown, porDefecto: string) =>
    (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? porDefecto

  const invitarMut = useMutation({
    mutationFn: (u: Usuario) => usuariosApi.invitar(u.id).then((resultado) => ({ usuario: u, resultado })),
    onSuccess: (r) => { setInvitacion(r); setAviso(null) },
    onError: (e: unknown) => setAviso({ variante: 'error', texto: errorDe(e, 'No se pudo emitir la invitación') }),
  })

  // Pendientes del condominio a la vista: el admin ve el suyo; el super admin debe elegir uno en el filtro
  const condominioMasivo = isSuperAdmin
    ? (filtroCondominio && filtroCondominio !== 'sin' ? Number(filtroCondominio) : null)
    : (me?.condominio_id ?? null)
  const pendientesMasivo = condominioMasivo === null ? []
    : usuarios.filter((u) => u.estado === 'pendiente' && u.condominio_id === condominioMasivo)

  const masivaMut = useMutation({
    mutationFn: () => usuariosApi.invitarPendientes(isSuperAdmin ? condominioMasivo ?? undefined : undefined),
    onSuccess: ({ enviados, fallidos }) => setAviso({
      variante: fallidos ? 'error' : 'success',
      texto: `Invitaciones enviadas por correo: ${enviados}.`
        + (fallidos ? ` Fallaron ${fallidos}: reenvíalas una a una o por WhatsApp.` : ''),
    }),
    onError: (e: unknown) => setAviso({ variante: 'error', texto: errorDe(e, 'No se pudieron enviar las invitaciones') }),
  })

  const invitarTodos = () => {
    if (window.confirm(`Se enviará un correo de invitación a ${pendientesMasivo.length} persona(s) que aún no crean su clave. ¿Continuar?`)) {
      masivaMut.mutate()
    }
  }

  const openEdit = (u: Usuario) => {
    setEditForm({
      nombre: u.nombre,
      email: u.email,
      telefono: u.telefono ?? '',
      password: '',
      rol_id: String(u.rol_id),
      condominio_id: u.condominio_id ? String(u.condominio_id) : '',
      parcela_ids: u.parcelas.map((p) => p.id),
    })
    setEditUser(u)
    setError('')
  }

  const submitCreate = () => {
    setError('')
    const telefono = normalizarTelefono(createForm.telefono)
    if (telefono === undefined) { setError('Revisa el teléfono'); return }
    createMut.mutate({
      telefono,
      nombre: createForm.nombre,
      email: createForm.email,
      password: createForm.password || undefined,   // sin clave: cuenta pendiente, se invita
      rol_id: Number(createForm.rol_id),
      condominio_id: createForm.condominio_id ? Number(createForm.condominio_id) : (me?.condominio_id ?? undefined),
      parcela_ids: createForm.parcela_ids,
    })
  }

  const submitEdit = () => {
    if (!editUser) return
    setError('')
    const telefono = normalizarTelefono(editForm.telefono)
    if (telefono === undefined) { setError('Revisa el teléfono'); return }
    const payload: Record<string, unknown> = {
      telefono,
      nombre: editForm.nombre,
      email: editForm.email,
      rol_id: Number(editForm.rol_id),
      condominio_id: editForm.condominio_id ? Number(editForm.condominio_id) : null,
      parcela_ids: editForm.parcela_ids,
    }
    if (editForm.password) payload.password = editForm.password
    updateMut.mutate({ id: editUser.id, data: payload })
  }

  if (isLoading) return (
    <div className="flex h-64 items-center justify-center">
      <Spinner size="lg" className="text-primary-500" />
    </div>
  )

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Usuarios</h1>
          <p className="text-sm text-slate-500">
            {usuariosFiltrados.length} de {usuarios.length} usuarios
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
              <option value="sin">— Sin condominio</option>
            </select>
          )}
          {pendientesMasivo.length > 0 && (
            <Button variant="secondary" loading={masivaMut.isPending} onClick={invitarTodos}>
              <Mail className="h-4 w-4" /> Invitar pendientes ({pendientesMasivo.length})
            </Button>
          )}
          <Button onClick={() => { setCreateForm({ ...EMPTY_FORM, condominio_id: filtroCondominio && filtroCondominio !== 'sin' ? filtroCondominio : (me?.condominio_id ? String(me.condominio_id) : '') }); setCreateOpen(true) }}>
            <Plus className="h-4 w-4" /> Nuevo usuario
          </Button>
        </div>
      </div>

      {aviso && <Alert variant={aviso.variante}>{aviso.texto}</Alert>}

      <Card padding={false}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="px-5 py-3">Nombre</th>
              <th className="px-5 py-3">Email</th>
              <th className="px-5 py-3">Rol</th>
              <th className="px-5 py-3">Cuenta</th>
              <th className="px-5 py-3">Condominio</th>
              <th className="px-5 py-3">Parcelas</th>
              <th className="px-5 py-3">Último acceso</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {usuariosFiltrados.map((u) => (
              <tr key={u.id} className={`border-b border-slate-700/50 hover:bg-slate-700/20 ${u.id === me?.id ? 'bg-primary-600/5' : ''}`}>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    <UserCircle className="h-5 w-5 text-slate-500" />
                    <span className="font-medium text-slate-200">{u.nombre}</span>
                  </div>
                </td>
                <td className="px-5 py-3 text-slate-400">{u.email}{u.telefono && <span className="block text-xs text-slate-500">{formatearTelefono(u.telefono)}</span>}</td>
                <td className="px-5 py-3">
                  <Badge color={ROLE_COLOR[u.rol?.nombre] ?? 'slate'}>{u.rol?.nombre}</Badge>
                </td>
                <td className="px-5 py-3">
                  {u.estado === 'pendiente'
                    ? <Badge color="yellow">Pendiente</Badge>
                    : <Badge color="green">Activa</Badge>}
                </td>
                <td className="px-5 py-3 text-slate-400 text-sm">{condominioNombre(u.condominio_id)}</td>
                <td className="px-5 py-3 text-slate-400">
                  {u.parcelas.length > 0 ? u.parcelas.map((p) => p.numero_parcela).join(', ') : '—'}
                </td>
                <td className="px-5 py-3 text-slate-500">{fecha(u.ultimo_login)}</td>
                <td className="px-5 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {u.estado === 'pendiente' && (
                      <Button size="sm" variant="ghost" title="Enviar invitación para crear su clave"
                              loading={invitarMut.isPending && invitarMut.variables?.id === u.id}
                              onClick={() => invitarMut.mutate(u)}>
                        <Send className="h-3.5 w-3.5" /> Invitar
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" title="Editar" onClick={() => openEdit(u)}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {invitacion && (
        <InvitacionModal
          usuario={invitacion.usuario}
          resultado={invitacion.resultado}
          condominio={condominioNombre(invitacion.usuario.condominio_id)}
          onClose={() => setInvitacion(null)}
        />
      )}

      {/* Modal Crear */}
      <Modal open={createOpen} onClose={() => { setCreateOpen(false); setError('') }} title="Nuevo usuario" size="md">
        <div className="space-y-4">
          {error && <Alert variant="error">{error}</Alert>}
          <UsuarioForm
            form={createForm}
            onChange={(patch) => setCreateForm((f) => ({ ...f, ...patch }))}
            condominios={condominios}
            parcelas={parcelas}
            isSuperAdmin={isSuperAdmin}
            isEdit={false}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => { setCreateOpen(false); setError('') }}>Cancelar</Button>
            <Button loading={createMut.isPending} onClick={submitCreate}>Crear usuario</Button>
          </div>
        </div>
      </Modal>

      {/* Modal Editar */}
      <Modal open={!!editUser} onClose={() => { setEditUser(null); setError('') }} title={`Editar — ${editUser?.nombre}`} size="md">
        <div className="space-y-4">
          {error && <Alert variant="error">{error}</Alert>}
          <UsuarioForm
            form={editForm}
            onChange={(patch) => setEditForm((f) => ({ ...f, ...patch }))}
            condominios={condominios}
            parcelas={parcelas}
            isSuperAdmin={isSuperAdmin}
            isEdit
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => { setEditUser(null); setError('') }}>Cancelar</Button>
            <Button loading={updateMut.isPending} onClick={submitEdit}>Guardar cambios</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}


/** Resultado de una invitación: estado del correo y reenvío por WhatsApp o copiando el enlace. */
function InvitacionModal({ usuario, resultado, condominio, onClose }: {
  usuario: Usuario
  resultado: Invitacion
  condominio: string
  onClose: () => void
}) {
  const [copiado, setCopiado] = useState(false)
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(resultado.enlace)
      setCopiado(true)
    } catch { /* sin permiso de portapapeles: el enlace queda visible para copiarlo a mano */ }
  }
  const whatsapp = usuario.telefono
    ? urlWhatsApp(usuario.telefono, mensajeInvitacion(usuario.nombre, condominio, resultado.enlace))
    : null

  return (
    <Modal open onClose={onClose} title={`Invitación — ${usuario.nombre}`} size="md">
      <div className="space-y-4">
        {resultado.correo_enviado
          ? <Alert variant="success">Enviamos el correo a {usuario.email}. El enlace vence en 7 días y sirve una sola vez.</Alert>
          : <Alert variant="warning">No se envió el correo: {resultado.motivo}. Reenvía el enlace por WhatsApp o cópialo.</Alert>}
        <div className="flex flex-col gap-2 sm:flex-row">
          {whatsapp && (
            <a href={whatsapp} target="_blank" rel="noopener noreferrer" className="flex-1">
              <Button fullWidth variant="secondary"><MessageCircle className="h-4 w-4" /> Enviar por WhatsApp</Button>
            </a>
          )}
          <Button className="flex-1" variant="secondary" onClick={copiar}>
            {copiado ? <><Check className="h-4 w-4" /> Copiado</> : <><Copy className="h-4 w-4" /> Copiar enlace</>}
          </Button>
        </div>
        {!usuario.telefono && <p className="text-xs text-slate-500">Sin teléfono registrado: no se puede enviar por WhatsApp.</p>}
        <p className="break-all rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-400">{resultado.enlace}</p>
        <p className="text-xs text-slate-500">
          Comparte este enlace solo con {usuario.nombre}: quien lo abra puede crear la clave de esta cuenta.
        </p>
        <div className="flex justify-end"><Button onClick={onClose}>Cerrar</Button></div>
      </div>
    </Modal>
  )
}
