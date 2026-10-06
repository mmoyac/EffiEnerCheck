import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import type { AxiosError } from 'axios'
import { rifasApi } from '../../api/rifas'
import { Modal } from '../ui/Modal'
import { Button } from '../ui/Button'
import { Alert } from '../ui/Alert'
import { Input } from '../ui/Input'
import { Spinner } from '../ui/Spinner'
import { clp } from '../../utils/format'
import type { Rifa } from '../../types'

/** Eliminación de una rifa (solo super admin): resumen de lo que se borra y confirmación con el nombre. */
export function EliminarRifaModal({ rifa, open, onClose }: { rifa: Rifa; open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [confirmacion, setConfirmacion] = useState('')
  const [error, setError] = useState('')

  const { data: resumen, isLoading } = useQuery({
    queryKey: ['rifa-eliminacion', rifa.id],
    queryFn: () => rifasApi.resumenEliminacion(rifa.id),
    enabled: open,
  })

  const eliminarMut = useMutation({
    mutationFn: () => rifasApi.eliminar(rifa.id, confirmacion),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rifas'] })
      qc.removeQueries({ queryKey: ['rifa', rifa.id] })
      navigate('/rifas', { replace: true })
    },
    onError: (err) => setError((err as AxiosError<{ detail: string }>)?.response?.data?.detail ?? 'No se pudo eliminar'),
  })

  const coincide = confirmacion.trim() === rifa.nombre.trim()
  const cerrar = () => { setConfirmacion(''); setError(''); onClose() }

  return (
    <Modal open={open} onClose={cerrar} title="Eliminar rifa" size="md">
      {isLoading || !resumen ? (
        <div className="flex justify-center py-6"><Spinner /></div>
      ) : (
        <div className="space-y-4">
          <Alert variant="error">
            Se eliminará <strong>{rifa.nombre}</strong> y todo lo que depende de ella. Esta acción no se puede deshacer.
          </Alert>
          <ul className="space-y-1 rounded-lg bg-slate-900 p-3 text-sm text-slate-300">
            <li>Compras vigentes: <strong>{resumen.compras_vigentes}</strong> ({resumen.numeros_vendidos} números)</li>
            <li>Compras anuladas: <strong>{resumen.compras_anuladas}</strong></li>
            <li>Monto pagado: <strong>{clp(resumen.monto_pagado)}</strong></li>
            <li>Imputaciones al gasto común: <strong>{resumen.imputaciones_pendientes + resumen.imputaciones_cargadas}</strong>
              {resumen.imputaciones_cargadas > 0 && ` (${resumen.imputaciones_cargadas} ya cargadas)`}</li>
            <li>Fotos de vouchers: <strong>{resumen.vouchers}</strong></li>
          </ul>
          {resumen.imputaciones_cargadas > 0 && (
            <Alert variant="error">
              Hay {resumen.imputaciones_cargadas} imputación(es) ya cargada(s) en Comunidad Feliz: esos cobros seguirán en el
              gasto común y deberás revertirlos allá a mano.
            </Alert>
          )}
          {error && <Alert variant="error">{error}</Alert>}
          <Input
            label={`Para confirmar, escribe el nombre de la rifa: ${rifa.nombre}`}
            value={confirmacion}
            onChange={(e) => setConfirmacion(e.target.value)}
            autoComplete="off"
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={cerrar} disabled={eliminarMut.isPending}>Cancelar</Button>
            <Button variant="danger" disabled={!coincide} loading={eliminarMut.isPending} onClick={() => eliminarMut.mutate()}>
              Eliminar definitivamente
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}
