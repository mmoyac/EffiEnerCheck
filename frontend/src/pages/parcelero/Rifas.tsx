import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, ChevronLeft, ChevronRight, Clock, HeartHandshake, Trophy } from 'lucide-react'
import { rifasApi } from '../../api/rifas'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Spinner } from '../../components/ui/Spinner'
import { Alert } from '../../components/ui/Alert'
import { Header } from '../../components/layout/Header'
import { CompraPanel } from '../../components/rifas/CompraPanel'
import { ComprasLista } from '../../components/rifas/ComprasLista'
import { clp, fecha } from '../../utils/format'
import { useAuth } from '../../hooks/useAuth'

function Cargando() {
  return (
    <div className="flex h-48 items-center justify-center">
      <Spinner size="lg" className="text-primary-500" />
    </div>
  )
}

function ListaRifas() {
  const navigate = useNavigate()
  const { data: rifas = [], isLoading } = useQuery({ queryKey: ['rifas'], queryFn: () => rifasApi.list() })

  return (
    <>
      <div>
        <Link
          to="/liquidaciones"
          className="mb-4 flex items-center gap-1 text-sm font-medium text-primary-500 transition-colors hover:text-primary-400"
        >
          <ChevronLeft className="h-4 w-4" /> Volver a mis liquidaciones
        </Link>
        <h1 className="text-xl font-bold text-slate-100">Rifas solidarias</h1>
        <p className="text-sm text-slate-500">Compra números y revisa lo que tu parcela ha comprado</p>
      </div>

      {isLoading ? (
        <Cargando />
      ) : rifas.length === 0 ? (
        <Alert variant="info">No hay rifas en tu condominio por ahora.</Alert>
      ) : (
        <div className="space-y-3">
          {rifas.map((r) => (
            <button
              key={r.id}
              onClick={() => navigate(`/mis-rifas/${r.id}`)}
              className="flex w-full items-center justify-between rounded-xl bg-slate-800 p-4 text-left transition-all hover:bg-slate-700 active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <div className="min-w-0">
                <p className="truncate font-semibold text-slate-100">{r.nombre}</p>
                <p className="mt-0.5 truncate text-xs text-slate-400">A beneficio de {r.beneficiario} · {clp(r.precio_numero)} c/u</p>
              </div>
              <div className="ml-3 flex shrink-0 items-center gap-2">
                {r.estado === 'abierta' ? <Badge color="green" dot>Abierta</Badge> : <Badge color="slate">Cerrada</Badge>}
                <ChevronRight className="h-5 w-5 text-slate-500" />
              </div>
            </button>
          ))}
        </div>
      )}
    </>
  )
}

function DetalleRifa({ rifaId }: { rifaId: number }) {
  const { user } = useAuth()
  const misParcelas = user?.parcelas ?? []
  const { data: rifa, isLoading, error } = useQuery({ queryKey: ['rifa', rifaId], queryFn: () => rifasApi.get(rifaId) })

  if (isLoading) return <Cargando />
  if (error || !rifa) return <Alert variant="error">No se pudo cargar la rifa.</Alert>

  const abierta = rifa.estado === 'abierta'

  return (
    <>
      <div>
        <Link
          to="/mis-rifas"
          className="mb-4 flex items-center gap-1 text-sm font-medium text-primary-500 transition-colors hover:text-primary-400"
        >
          <ChevronLeft className="h-4 w-4" /> Volver a rifas
        </Link>
        <div className="flex items-start justify-between gap-3">
          <h1 className="text-xl font-bold text-slate-100">{rifa.nombre}</h1>
          {abierta ? <Badge color="green" dot>Abierta</Badge> : <Badge color="slate">Cerrada</Badge>}
        </div>
        <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-300">
          <HeartHandshake className="h-4 w-4 text-primary-400" /> A beneficio de {rifa.beneficiario}
        </p>
        {rifa.descripcion && <p className="mt-2 text-sm text-slate-400">{rifa.descripcion}</p>}
        <p className="mt-2 text-sm text-slate-400">
          {clp(rifa.precio_numero)} por número · {rifa.numeros_vendidos_total} de {rifa.cantidad_numeros} vendidos
        </p>
      </div>

      {rifa.premios.length > 0 && (
        <Card>
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-300">
            <Trophy className="h-4 w-4 text-yellow-400" /> Premios
          </p>
          <ol className="space-y-1 text-sm text-slate-200">
            {rifa.premios.map((p, i) => (
              <li key={i} className="flex gap-2"><span className="w-5 shrink-0 text-right font-mono text-slate-500">{i + 1}.</span>{p}</li>
            ))}
          </ol>
        </Card>
      )}

      {/* Imputaciones al gasto común: existen cuando la rifa está cerrada */}
      {rifa.imputaciones.map((imp) => (
        <Card key={imp.id}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Parcela {imp.parcela_numero}</p>
              <p className="text-sm text-slate-400">
                {imp.cantidad_numeros} {imp.cantidad_numeros === 1 ? 'número' : 'números'} con cargo al gasto común
              </p>
            </div>
            <span className="font-mono text-xl font-bold text-primary-400">{clp(imp.monto)}</span>
          </div>
          {imp.cargada ? (
            <div className="mt-3 flex items-center gap-2 text-sm text-green-400">
              <CheckCircle2 className="h-4 w-4" /> Incluido en tu gasto común ({fecha(imp.cargada_at)})
            </div>
          ) : (
            <div className="mt-3 flex items-center gap-2 text-sm text-yellow-400">
              <Clock className="h-4 w-4" /> Se incluirá en tu próximo gasto común
            </div>
          )}
        </Card>
      ))}

      {abierta ? (
        misParcelas.length === 0 ? (
          <Alert variant="warning">Tu usuario no tiene parcelas asociadas. Pide a la administración que te vincule a tu parcela.</Alert>
        ) : (
          <Card>
            <p className="mb-3 text-sm font-semibold text-slate-300">Elige tus números</p>
            <CompraPanel rifa={rifa} modo="portal" parcelas={misParcelas} barraFija />
          </Card>
        )
      ) : (
        rifa.compras.every((c) => c.anulada) && <Alert variant="info">La rifa está cerrada y tu parcela no compró números.</Alert>
      )}

      <Card>
        <p className="mb-3 text-sm font-semibold text-slate-300">Compras de {misParcelas.length > 1 ? 'tus parcelas' : 'tu parcela'}</p>
        <ComprasLista rifaId={rifa.id} compras={rifa.compras} mostrarParcela={misParcelas.length > 1} vacio="Tu parcela aún no ha comprado números." />
      </Card>
    </>
  )
}

export default function MisRifas() {
  const { id } = useParams()
  return (
    <div className="min-h-screen bg-slate-900">
      <Header />
      <div className="mx-auto max-w-lg space-y-5 px-4 py-6 pb-28">
        {id ? <DetalleRifa rifaId={Number(id)} /> : <ListaRifas />}
      </div>
    </div>
  )
}
