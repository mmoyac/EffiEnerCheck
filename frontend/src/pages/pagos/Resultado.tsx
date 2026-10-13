import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, ChevronLeft, Clock, Loader2, RefreshCw, XCircle } from 'lucide-react'
import type { AxiosError } from 'axios'
import { pagosApi } from '../../api/pagos'
import { Header } from '../../components/layout/Header'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Spinner } from '../../components/ui/Spinner'
import { clp, fechaHora } from '../../utils/format'
import type { IntencionPago } from '../../types'

// Mientras el pago siga en proceso: el estado se lee cada 3 s y se pide al backend consultar al
// proveedor cada 15 s, durante 5 min (una transferencia puede quedar "verificando" varios minutos).
const LEER_CADA_MS = 3_000
const CONSULTAR_CADA_MS = 15_000
const ESPERA_MAXIMA_MS = 5 * 60_000

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function Fila({ etiqueta, valor }: { etiqueta: string; valor: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 text-sm">
      <span className="shrink-0 text-slate-400">{etiqueta}</span>
      <span className="min-w-0 break-words text-right text-slate-200">{valor}</span>
    </div>
  )
}

function Detalle({ pago }: { pago: IntencionPago }) {
  return (
    <div className="space-y-2 rounded-xl bg-slate-700/40 p-4">
      <Fila etiqueta="Concepto" valor={pago.descripcion} />
      <Fila etiqueta="Pasarela" valor={pago.pasarela_nombre} />
      {pago.numero_operacion && <Fila etiqueta="N° de operación" valor={<span className="font-mono">{pago.numero_operacion}</span>} />}
      {pago.medio && <Fila etiqueta="Medio" valor={pago.ultimos_digitos ? `${pago.medio} ···· ${pago.ultimos_digitos}` : pago.medio} />}
      {pago.comision > 0 && <Fila etiqueta="Comisión" valor={clp(pago.comision)} />}
      <Fila etiqueta="Total" valor={<span className="font-mono font-bold">{clp(pago.total)}</span>} />
      {pago.confirmado_at && <Fila etiqueta="Fecha" valor={fechaHora(pago.confirmado_at)} />}
    </div>
  )
}

function Encabezado({ estado }: { estado: IntencionPago['estado'] }) {
  const config = {
    CONFIRMADO: { icono: CheckCircle2, color: 'text-green-400', titulo: 'Pago aprobado' },
    RECHAZADO: { icono: XCircle, color: 'text-red-400', titulo: 'El pago no se realizó' },
    EN_REVISION: { icono: AlertTriangle, color: 'text-yellow-400', titulo: 'Pago en revisión' },
    EXPIRADO: { icono: Clock, color: 'text-slate-400', titulo: 'El pago expiró' },
    INICIADO: { icono: Loader2, color: 'text-primary-400 animate-spin', titulo: 'Pago en proceso' },
  }[estado]
  const Icono = config.icono
  return (
    <div className="flex flex-col items-center gap-3 py-2 text-center">
      <Icono className={`h-14 w-14 ${config.color}`} />
      <h1 className="text-xl font-bold text-slate-100">{config.titulo}</h1>
    </div>
  )
}

function mensaje(pago: IntencionPago, agotado: boolean): string {
  switch (pago.estado) {
    case 'CONFIRMADO':
      return 'Tu pago quedó registrado. Ya puedes ver tu compra.'
    case 'RECHAZADO':
      return `${pago.motivo ?? 'La pasarela no aprobó el pago'}. No se te cobró y los números quedaron libres.`
    case 'EN_REVISION':
      return pago.motivo?.includes('anulada después de pagada')
        ? 'La administración anuló esta compra después de tu pago. Te devolverá el dinero por la misma pasarela; ante dudas, contáctala.'
        : 'Recibimos tu pago, pero no pudimos aplicarlo automáticamente. La administración lo revisará y te contactará.'
    case 'EXPIRADO':
      return 'No recibimos la confirmación a tiempo y los números se liberaron. Si la pasarela te cobró, el pago se aplicará igual en cuanto lo confirme.'
    default:
      return agotado
        ? 'La pasarela aún no confirma el pago. Puede tardar unos minutos (las transferencias se verifican con el banco). Vuelve a consultar en un rato.'
        : 'Estamos esperando la confirmación de la pasarela. No cierres esta pantalla.'
  }
}

export default function ResultadoPago() {
  const { id = '' } = useParams()
  const qc = useQueryClient()
  const valido = UUID.test(id)
  const inicio = useRef(Date.now())
  const [agotado, setAgotado] = useState(false)
  const [consultando, setConsultando] = useState(false)

  const { data: pago, isLoading, error } = useQuery({
    queryKey: ['pago', id],
    queryFn: () => pagosApi.get(id),
    enabled: valido,
    retry: false,
    refetchInterval: (q) => (q.state.data?.estado === 'INICIADO' && !agotado ? LEER_CADA_MS : false),
  })
  const enProceso = pago?.estado === 'INICIADO'

  const consultar = async () => {
    setConsultando(true)
    try {
      qc.setQueryData(['pago', id], await pagosApi.consultar(id))
    } catch (err) {
      // 429: se consultó hace menos de 10 s; la próxima lectura trae lo último
      if ((err as AxiosError)?.response?.status !== 429) throw err
    } finally {
      setConsultando(false)
    }
  }

  // Consulta al proveedor cada 15 s mientras siga en proceso, hasta 5 minutos
  useEffect(() => {
    if (!enProceso || agotado) return
    const t = setInterval(() => {
      if (Date.now() - inicio.current > ESPERA_MAXIMA_MS) {
        setAgotado(true)
        return
      }
      consultar().catch(() => undefined)
    }, CONSULTAR_CADA_MS)
    return () => clearInterval(t)
  }, [enProceso, agotado]) // eslint-disable-line react-hooks/exhaustive-deps

  const reintentar = () => {
    inicio.current = Date.now()
    setAgotado(false)
    consultar().catch(() => undefined)
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <Header />
      <div className="mx-auto max-w-lg space-y-5 px-4 py-6">
        {!valido || error ? (
          <>
            <Alert variant="error">No encontramos este pago. Si pagaste, revisa tus compras: el pago se aplica igual cuando la pasarela lo confirma.</Alert>
            <Link to="/" className="inline-flex items-center gap-1 text-sm font-medium text-primary-500 hover:text-primary-400">
              <ChevronLeft className="h-4 w-4" /> Ir al inicio
            </Link>
          </>
        ) : isLoading || !pago ? (
          <div className="flex h-48 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
        ) : (
          <Card>
            <div className="space-y-5">
              <Encabezado estado={pago.estado} />
              <p className="text-center text-sm text-slate-300">{mensaje(pago, agotado)}</p>
              <Detalle pago={pago} />
              <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
                {enProceso && (
                  <Button variant="secondary" loading={consultando} onClick={reintentar}>
                    <RefreshCw className="h-4 w-4" /> Consultar de nuevo
                  </Button>
                )}
                {pago.volver_a && (
                  <Link to={pago.volver_a} className="inline-flex items-center justify-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500">
                    {pago.estado === 'CONFIRMADO' ? 'Ver mis compras' : 'Volver'}
                  </Link>
                )}
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
