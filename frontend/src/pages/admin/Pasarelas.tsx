import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { AlertTriangle, CheckCircle2, CreditCard, KeyRound, Pencil, Plug, Plus, Power, Trash2, XCircle } from 'lucide-react'
import { condominiosApi } from '../../api/condominios'
import { pagosApi, pasarelasApi } from '../../api/pagos'
import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'
import { Modal } from '../../components/ui/Modal'
import { Spinner } from '../../components/ui/Spinner'
import { useRole } from '../../hooks/useAuth'
import { PagosPorRevisar } from '../../components/pagos/PagosPorRevisar'
import { clp, fechaHora } from '../../utils/format'
import type { AmbientePasarela, IntencionRevision, Pasarela, ProveedorPago } from '../../types'

function errorMsg(err: unknown): string {
  const detail = (err as AxiosError<{ detail: unknown }>)?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg?.replace(/^Value error, /, '')).join(' · ')
  return 'Error desconocido'
}

const AMBIENTE_TEXTO: Record<AmbientePasarela, string> = { integracion: 'Integración (pruebas)', produccion: 'Producción' }

function comisionTexto(p: Pick<Pasarela, 'comision_porcentaje' | 'comision_fija'>): string {
  const pct = Number(p.comision_porcentaje)
  const partes = [pct ? `${pct.toLocaleString('es-CL', { maximumFractionDigits: 4 })} %` : null, p.comision_fija ? clp(p.comision_fija) : null].filter(Boolean)
  return partes.length ? partes.join(' + ') : 'Sin comisión'
}

// ---------------------------------------------------------------------------
// Formularios
// ---------------------------------------------------------------------------

function CamposCredenciales({ proveedor, valores, onChange }: {
  proveedor: ProveedorPago | undefined
  valores: Record<string, string>
  onChange: (v: Record<string, string>) => void
}) {
  if (!proveedor) return null
  return (
    <div className="space-y-3 rounded-lg border border-slate-700 p-3">
      <p className="flex items-center gap-2 text-sm font-semibold text-slate-300"><KeyRound className="h-4 w-4" /> Credenciales de {proveedor.nombre}</p>
      {proveedor.campos_credenciales.map((c) => (
        <Input
          key={c.nombre}
          label={c.etiqueta}
          type={c.secreto ? 'password' : 'text'}
          autoComplete="off"
          value={valores[c.nombre] ?? ''}
          onChange={(e) => onChange({ ...valores, [c.nombre]: e.target.value })}
          required
        />
      ))}
      <p className="text-xs text-slate-500">Se guardan cifradas y nunca se vuelven a mostrar. Para cambiarlas, se reemplazan.</p>
    </div>
  )
}

function PasarelaModal({ open, onClose, condominioId, pasarela, proveedores }: {
  open: boolean
  onClose: () => void
  condominioId: number
  pasarela: Pasarela | null
  proveedores: ProveedorPago[]
}) {
  const qc = useQueryClient()
  const [proveedor, setProveedor] = useState('')
  const [nombre, setNombre] = useState('')
  const [ambiente, setAmbiente] = useState<AmbientePasarela>('integracion')
  const [porcentaje, setPorcentaje] = useState('0')
  const [fija, setFija] = useState('0')
  const [orden, setOrden] = useState('0')
  const [credenciales, setCredenciales] = useState<Record<string, string>>({})
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setProveedor(pasarela?.proveedor ?? proveedores[0]?.proveedor ?? '')
    setNombre(pasarela?.nombre_visible ?? '')
    setAmbiente(pasarela?.ambiente ?? 'integracion')
    setPorcentaje(pasarela ? String(Number(pasarela.comision_porcentaje)) : '0')
    setFija(String(pasarela?.comision_fija ?? 0))
    setOrden(String(pasarela?.orden ?? 0))
    setCredenciales({})
    setError('')
  }, [open, pasarela, proveedores])

  const prov = proveedores.find((p) => p.proveedor === proveedor)
  const comision = { comision_porcentaje: porcentaje.replace(',', '.') || '0', comision_fija: Number(fija) || 0, orden: Number(orden) || 0 }

  const mut = useMutation({
    mutationFn: () =>
      pasarela
        ? pasarelasApi.update(pasarela.id, { nombre_visible: nombre.trim(), ambiente, ...comision })
        : pasarelasApi.create({ condominio_id: condominioId, proveedor, nombre_visible: nombre.trim(), ambiente, credenciales, ...comision }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['pasarelas'] }); onClose() },
    onError: (err) => setError(errorMsg(err)),
  })

  return (
    <Modal open={open} onClose={onClose} title={pasarela ? 'Editar pasarela' : 'Nueva pasarela'} size="lg">
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setError(''); mut.mutate() }}>
        {!pasarela && (
          <div className="flex flex-col gap-1">
            <label htmlFor="pasarela-proveedor" className="text-sm font-medium text-slate-300">Proveedor</label>
            <select id="pasarela-proveedor" value={proveedor} onChange={(e) => { setProveedor(e.target.value); setCredenciales({}) }}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 focus:border-primary-500 focus:outline-none">
              {proveedores.map((p) => <option key={p.proveedor} value={p.proveedor}>{p.nombre}</option>)}
            </select>
            {prov && (
              <p className="text-xs text-slate-500">
                Monto mínimo {clp(prov.monto_minimo)}{prov.requiere_email ? ' · exige el correo del pagador' : ''}
              </p>
            )}
          </div>
        )}
        <Input label="Nombre que ve el comunero" value={nombre} onChange={(e) => setNombre(e.target.value)}
          placeholder="Ej: Tarjeta o Webpay" maxLength={60} required />
        <div className="flex flex-col gap-1">
          <label htmlFor="pasarela-ambiente" className="text-sm font-medium text-slate-300">Ambiente</label>
          <select id="pasarela-ambiente" value={ambiente} onChange={(e) => setAmbiente(e.target.value as AmbientePasarela)}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 focus:border-primary-500 focus:outline-none">
            <option value="integracion">{AMBIENTE_TEXTO.integracion}</option>
            <option value="produccion">{AMBIENTE_TEXTO.produccion}</option>
          </select>
          <p className="text-xs text-slate-500">
            Cada ambiente es una cuenta distinta del proveedor. En producción nunca se ofrece una pasarela de integración.
            {pasarela && ambiente !== pasarela.ambiente && ' Cambiar el ambiente desactiva la pasarela.'}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Input label="Comisión (% con IVA)" inputMode="decimal" value={porcentaje} onChange={(e) => setPorcentaje(e.target.value)} />
          <Input label="Comisión fija (CLP)" type="number" min={0} step={1} value={fija} onChange={(e) => setFija(e.target.value)} />
        </div>
        <p className="-mt-2 text-xs text-slate-500">La paga el comunero: se suma al total para que a la comunidad le llegue el valor completo.</p>
        <Input label="Orden" type="number" step={1} value={orden} onChange={(e) => setOrden(e.target.value)} hint="Menor = aparece primero" />
        {!pasarela && <CamposCredenciales proveedor={prov} valores={credenciales} onChange={setCredenciales} />}
        {error && <Alert variant="error">{error}</Alert>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={mut.isPending}>Cancelar</Button>
          <Button type="submit" loading={mut.isPending} disabled={!nombre.trim()}>{pasarela ? 'Guardar' : 'Crear pasarela'}</Button>
        </div>
      </form>
    </Modal>
  )
}

function CredencialesModal({ pasarela, proveedor, onClose }: { pasarela: Pasarela | null; proveedor: ProveedorPago | undefined; onClose: () => void }) {
  const qc = useQueryClient()
  const [valores, setValores] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  useEffect(() => { setValores({}); setError('') }, [pasarela])
  const mut = useMutation({
    mutationFn: () => pasarelasApi.credenciales(pasarela!.id, valores),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['pasarelas'] }); onClose() },
    onError: (err) => setError(errorMsg(err)),
  })
  return (
    <Modal open={!!pasarela} onClose={onClose} title="Reemplazar credenciales" size="md">
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setError(''); mut.mutate() }}>
        <Alert variant="warning">La pasarela queda desactivada hasta volver a probarla y activarla.</Alert>
        <CamposCredenciales proveedor={proveedor} valores={valores} onChange={setValores} />
        {error && <Alert variant="error">{error}</Alert>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={mut.isPending}>Cancelar</Button>
          <Button type="submit" loading={mut.isPending}>Reemplazar</Button>
        </div>
      </form>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Tarjeta de una pasarela
// ---------------------------------------------------------------------------

function TarjetaPasarela({ p, editable, onEditar, onCredenciales }: {
  p: Pasarela
  editable: boolean
  onEditar: () => void
  onCredenciales: () => void
}) {
  const qc = useQueryClient()
  const [aviso, setAviso] = useState<{ ok: boolean; texto: string } | null>(null)
  const refrescar = () => qc.invalidateQueries({ queryKey: ['pasarelas'] })
  const fallo = (err: unknown) => setAviso({ ok: false, texto: errorMsg(err) })

  const probarMut = useMutation({
    mutationFn: () => pasarelasApi.probar(p.id),
    onSuccess: (r) => { setAviso({ ok: r.ok, texto: r.mensaje }); refrescar() },
    onError: fallo,
  })
  const activarMut = useMutation({
    mutationFn: () => pasarelasApi.activar(p.id, !p.activa),
    onSuccess: () => { setAviso(null); refrescar() },
    onError: fallo,
  })
  const eliminarMut = useMutation({
    mutationFn: () => pasarelasApi.remove(p.id),
    onSuccess: refrescar,
    onError: fallo,
  })

  return (
    <Card>
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="break-words font-semibold text-slate-100">{p.nombre_visible}</p>
            <p className="text-xs text-slate-400">{p.proveedor_nombre} · {comisionTexto(p)}</p>
          </div>
          <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
            <Badge color={p.ambiente === 'produccion' ? 'blue' : 'purple'}>{p.ambiente === 'produccion' ? 'Producción' : 'Integración'}</Badge>
            {p.activa ? <Badge color="green" dot>Activa</Badge> : <Badge color="slate">Inactiva</Badge>}
          </div>
        </div>

        <div className="space-y-1 text-xs text-slate-400">
          <p>Credenciales: {p.credenciales_cargadas ? `cargadas${p.credenciales_at ? ` el ${fechaHora(p.credenciales_at)}` : ''}` : 'sin cargar'}</p>
          <p className="flex items-center gap-1">
            {p.prueba_at == null ? (
              'Conexión sin probar'
            ) : (
              <>
                {p.prueba_ok ? <CheckCircle2 className="h-3.5 w-3.5 text-green-400" /> : <XCircle className="h-3.5 w-3.5 text-red-400" />}
                <span className="min-w-0">{p.prueba_mensaje} · {fechaHora(p.prueba_at)}{p.prueba_ok && !p.prueba_vigente ? ' (anterior a las credenciales actuales)' : ''}</span>
              </>
            )}
          </p>
        </div>

        {aviso && <Alert variant={aviso.ok ? 'success' : 'error'}>{aviso.texto}</Alert>}

        {editable && (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" loading={probarMut.isPending} onClick={() => probarMut.mutate()}>
              <Plug className="h-4 w-4" /> Probar conexión
            </Button>
            <Button size="sm" variant={p.activa ? 'ghost' : 'primary'} loading={activarMut.isPending} onClick={() => activarMut.mutate()}>
              <Power className="h-4 w-4" /> {p.activa ? 'Desactivar' : 'Activar'}
            </Button>
            <Button size="sm" variant="ghost" onClick={onEditar}><Pencil className="h-4 w-4" /> Editar</Button>
            <Button size="sm" variant="ghost" onClick={onCredenciales}><KeyRound className="h-4 w-4" /> Credenciales</Button>
            {!p.tiene_pagos && (
              <Button size="sm" variant="ghost" loading={eliminarMut.isPending}
                onClick={() => { if (window.confirm(`¿Eliminar la pasarela «${p.nombre_visible}»?`)) eliminarMut.mutate() }}>
                <Trash2 className="h-4 w-4" /> Eliminar
              </Button>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Página
// ---------------------------------------------------------------------------

export default function Pasarelas() {
  const esSuper = useRole() === 'super_admin'
  const [condominioId, setCondominioId] = useState<number | null>(null)
  const [editando, setEditando] = useState<Pasarela | null>(null)
  const [creando, setCreando] = useState(false)
  const [credenciales, setCredenciales] = useState<Pasarela | null>(null)

  const { data: condominios = [] } = useQuery({ queryKey: ['condominios'], queryFn: condominiosApi.list, enabled: esSuper })
  useEffect(() => {
    if (esSuper && condominioId == null && condominios.length > 0) setCondominioId(condominios[0].id)
  }, [esSuper, condominios, condominioId])

  const { data: proveedores = [] } = useQuery({ queryKey: ['pasarelas-proveedores'], queryFn: pasarelasApi.proveedores, enabled: esSuper })
  const { data: pasarelas = [], isLoading } = useQuery({
    queryKey: ['pasarelas', esSuper ? condominioId : 'propio'],
    queryFn: () => pasarelasApi.list(esSuper ? condominioId ?? undefined : undefined),
    enabled: !esSuper || condominioId != null,
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-100"><CreditCard className="h-6 w-6 text-primary-400" /> Pasarelas de pago</h1>
          <p className="text-sm text-slate-500">
            {esSuper
              ? 'Cuentas de la comunidad en Flow, Khipu u otros, para que los comuneros paguen en línea.'
              : 'Las configura el equipo de la plataforma. Aquí ves cuáles están activas y su comisión.'}
          </p>
        </div>
        {esSuper && condominioId != null && (
          <Button onClick={() => setCreando(true)} disabled={proveedores.length === 0}><Plus className="h-4 w-4" /> Nueva pasarela</Button>
        )}
      </div>

      {esSuper && condominios.length > 1 && (
        <div className="flex flex-col gap-1 sm:max-w-xs">
          <label htmlFor="pasarelas-condominio" className="text-sm font-medium text-slate-300">Condominio</label>
          <select id="pasarelas-condominio" value={condominioId ?? ''} onChange={(e) => setCondominioId(Number(e.target.value))}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 focus:border-primary-500 focus:outline-none">
            {condominios.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
        </div>
      )}

      {isLoading ? (
        <div className="flex h-32 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
      ) : pasarelas.length === 0 ? (
        <Alert variant="info">
          {esSuper ? 'Este condominio no tiene pasarelas. Crea una para habilitar el pago en línea.' : 'Tu condominio aún no tiene pasarelas de pago.'}
        </Alert>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {pasarelas.map((p) => (
            <TarjetaPasarela key={p.id} p={p} editable={esSuper} onEditar={() => setEditando(p)} onCredenciales={() => setCredenciales(p)} />
          ))}
        </div>
      )}

      <PagosPorRevisar />

      {esSuper && condominioId != null && (
        <>
          <PasarelaModal
            open={creando || !!editando}
            onClose={() => { setCreando(false); setEditando(null) }}
            condominioId={condominioId}
            pasarela={editando}
            proveedores={proveedores}
          />
          <CredencialesModal
            pasarela={credenciales}
            proveedor={proveedores.find((x) => x.proveedor === credenciales?.proveedor)}
            onClose={() => setCredenciales(null)}
          />
        </>
      )}
    </div>
  )
}
