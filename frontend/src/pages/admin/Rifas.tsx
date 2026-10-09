import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { Plus, Ticket } from 'lucide-react'
import { rifasApi } from '../../api/rifas'
import { condominiosApi } from '../../api/condominios'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Spinner } from '../../components/ui/Spinner'
import { Alert } from '../../components/ui/Alert'
import { RifaFormModal } from './RifaFormModal'
import { clp, fecha } from '../../utils/format'
import { useRole } from '../../hooks/useAuth'
import type { RifaCreate } from '../../types'

export default function Rifas() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const isSuperAdmin = useRole() === 'super_admin'
  const [creando, setCreando] = useState(false)
  const [error, setError] = useState('')

  const { data: rifas = [], isLoading } = useQuery({ queryKey: ['rifas'], queryFn: () => rifasApi.list() })
  const { data: condominios = [] } = useQuery({ queryKey: ['condominios'], queryFn: condominiosApi.list, enabled: isSuperAdmin })

  const crearMut = useMutation({
    mutationFn: (body: RifaCreate) => rifasApi.create(body),
    onSuccess: (rifa) => {
      qc.invalidateQueries({ queryKey: ['rifas'] })
      setCreando(false)
      navigate(`/rifas/${rifa.id}`)
    },
    onError: (err: unknown) => {
      const msg = (err as AxiosError<{ detail: string }>)?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Revisa los datos ingresados')
    },
  })

  const condominioNombre = (id: number) => condominios.find((c) => c.id === id)?.nombre ?? `#${id}`

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Rifas solidarias</h1>
          <p className="text-sm text-slate-400">Se cobran aparte: no forman parte de la boleta eléctrica ni de las liquidaciones</p>
        </div>
        <Button onClick={() => { setError(''); setCreando(true) }}>
          <Plus className="h-4 w-4" /> Nueva rifa
        </Button>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
      ) : rifas.length === 0 ? (
        <Alert variant="info">Aún no hay rifas. Crea una para que los comuneros puedan comprar números desde su portal.</Alert>
      ) : (
        <Card padding={false}>
          {/* Celular: lista apilada, una tarjeta por rifa */}
          <ul className="divide-y divide-slate-700/50 md:hidden">
            {rifas.map((r) => (
              <li
                key={r.id}
                onClick={() => navigate(`/rifas/${r.id}`)}
                className="cursor-pointer space-y-2 px-4 py-3 transition-colors hover:bg-slate-700/40"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="flex min-w-0 items-center gap-2 font-medium text-slate-100">
                      <Ticket className="h-4 w-4 shrink-0 text-primary-400" /><span className="truncate">{r.nombre}</span>
                    </p>
                    <p className="break-words text-xs text-slate-400">A beneficio de {r.beneficiario}</p>
                    {isSuperAdmin && <p className="truncate text-xs text-slate-300">{condominioNombre(r.condominio_id)}</p>}
                  </div>
                  <div className="shrink-0">
                    {r.estado === 'abierta' ? <Badge color="green" dot>Abierta</Badge> : <Badge color="slate">Cerrada</Badge>}
                  </div>
                </div>
                <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs text-slate-400">
                  <span>Precio <span className="font-mono text-slate-300">{clp(r.precio_numero)}</span></span>
                  <span>Vendidos <span className="font-mono text-slate-300">{r.numeros_vendidos_total} / {r.cantidad_numeros}</span></span>
                  <span>Recaudado <span className="font-mono font-semibold text-primary-400">{clp(r.recaudado)}</span></span>
                  <span>Creada {fecha(r.created_at)}</span>
                </div>
              </li>
            ))}
          </ul>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-4 py-3">Rifa</th>
                  {isSuperAdmin && <th className="px-4 py-3">Condominio</th>}
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3 text-right">Precio</th>
                  <th className="px-4 py-3 text-right">Vendidos</th>
                  <th className="px-4 py-3 text-right">Recaudado</th>
                  <th className="px-4 py-3">Creada</th>
                </tr>
              </thead>
              <tbody>
                {rifas.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => navigate(`/rifas/${r.id}`)}
                    className="cursor-pointer border-b border-slate-700/50 transition-colors hover:bg-slate-700/40"
                  >
                    <td className="px-4 py-3">
                      <p className="flex items-center gap-2 font-medium text-slate-100"><Ticket className="h-4 w-4 text-primary-400" />{r.nombre}</p>
                      <p className="text-xs text-slate-400">A beneficio de {r.beneficiario}</p>
                    </td>
                    {isSuperAdmin && <td className="px-4 py-3 text-slate-300">{condominioNombre(r.condominio_id)}</td>}
                    <td className="px-4 py-3">
                      {r.estado === 'abierta' ? <Badge color="green" dot>Abierta</Badge> : <Badge color="slate">Cerrada</Badge>}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-300">{clp(r.precio_numero)}</td>
                    <td className="px-4 py-3 text-right font-mono text-slate-300">{r.numeros_vendidos_total} / {r.cantidad_numeros}</td>
                    <td className="px-4 py-3 text-right font-mono font-semibold text-primary-400">{clp(r.recaudado)}</td>
                    <td className="px-4 py-3 text-slate-400">{fecha(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <RifaFormModal
        open={creando}
        onClose={() => setCreando(false)}
        onSubmit={(body) => crearMut.mutate(body)}
        loading={crearMut.isPending}
        error={error}
        condominios={isSuperAdmin ? condominios : undefined}
      />
    </div>
  )
}
