import 'package:flutter/material.dart';

import '../../../core/network/api_client.dart';
import '../data/doctor_api.dart';
import 'doctor_prescription_form_screen.dart';

class DoctorConsultationDetailScreen extends StatefulWidget {
  const DoctorConsultationDetailScreen({
    super.key,
    required this.api,
    required this.consultationId,
  });
  final DoctorApi api;
  final int consultationId;

  @override
  State<DoctorConsultationDetailScreen> createState() =>
      _DoctorConsultationDetailScreenState();
}

class _DoctorConsultationDetailScreenState
    extends State<DoctorConsultationDetailScreen> {
  late Future<Map<String, dynamic>> _future = widget.api.consultation(
    widget.consultationId,
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Detalle de consulta')),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return _error(
            context,
            snapshot.error!,
            () => setState(
              () => _future = widget.api.consultation(widget.consultationId),
            ),
          );
        }
        final data = snapshot.data!;
        final prescriptions = (data['recetas'] as List? ?? const [])
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e))
            .toList();
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _field('Paciente', data['paciente_nombre']),
                    _field('Médico', data['medico_nombre']),
                    _field('Fecha', data['fecha']),
                    _field('Estado', data['estado_cita']),
                    _field('Motivo', data['motivo']),
                    _field('Observación', data['observacion']),
                    _field('Diagnóstico', data['diagnostico']),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Recetas',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                FilledButton.icon(
                  onPressed: () => _createPrescription(),
                  icon: const Icon(Icons.add),
                  label: const Text('Emitir'),
                ),
              ],
            ),
            if (prescriptions.isEmpty)
              const Padding(
                padding: EdgeInsets.all(12),
                child: Text('Esta consulta todavía no tiene recetas.'),
              ),
            for (final prescription in prescriptions)
              Card(
                child: ListTile(
                  title: Text(
                    'Receta #${prescription['id']} · ${prescription['cantidad_medicamentos'] ?? 0} medicamento(s)',
                  ),
                  subtitle: Text(
                    prescription['indicaciones']?.toString().isNotEmpty == true
                        ? prescription['indicaciones'].toString()
                        : 'Sin indicaciones generales',
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () =>
                      _viewPrescription((prescription['id'] as num).toInt()),
                ),
              ),
          ],
        );
      },
    ),
  );

  Future<void> _createPrescription() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => DoctorPrescriptionFormScreen(
          api: widget.api,
          consultationId: widget.consultationId,
        ),
      ),
    );
    if (saved == true) {
      final future = widget.api.consultation(widget.consultationId);
      setState(() {
        _future = future;
      });
    }
  }

  Future<void> _viewPrescription(int id) async {
    try {
      final data = await widget.api.prescription(id);
      if (!mounted) return;
      final medicines = (data['medicamentos'] as List? ?? const [])
          .whereType<Map>()
          .toList();
      final warnings = (data['advertencias_alergia'] as List? ?? const [])
          .whereType<Map>()
          .toList();
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (context) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: ListView(
              shrinkWrap: true,
              children: [
                Text(
                  'Receta #$id',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text('Paciente: ${data['paciente_nombre'] ?? '—'}'),
                Text('Fecha: ${data['fecha'] ?? '—'}'),
                Text(
                  'Indicaciones: ${data['indicaciones']?.toString().isNotEmpty == true ? data['indicaciones'] : 'Sin indicaciones generales'}',
                ),
                if (warnings.isNotEmpty) ...[
                  const Divider(),
                  const Text(
                    'Advertencias de alergias',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Colors.deepOrange,
                    ),
                  ),
                  for (final warning in warnings)
                    Text(
                      '• ${warning['mensaje'] ?? warning['nombre_alergia'] ?? 'Advertencia'} Severidad: ${warning['severidad'] ?? '—'}',
                    ),
                ],
                const Divider(),
                const Text(
                  'Medicamentos',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                for (final medicine in medicines)
                  ListTile(
                    title: Text(
                      medicine['nombre_medicamento']?.toString() ?? '',
                    ),
                    subtitle: Text(
                      'Dosis: ${medicine['dosis'] ?? '—'} · ${medicine['frecuencia'] ?? '—'} · ${medicine['duracion'] ?? '—'}',
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
      }
    }
  }
}

Widget _field(String label, dynamic value) => Padding(
  padding: const EdgeInsets.only(bottom: 12),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: const TextStyle(fontSize: 12, color: Colors.black54)),
      const SizedBox(height: 2),
      Text(value?.toString() ?? '—'),
    ],
  ),
);
Widget _error(BuildContext context, Object error, VoidCallback retry) => Center(
  child: Padding(
    padding: const EdgeInsets.all(24),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(apiErrorMessage(error), textAlign: TextAlign.center),
        const SizedBox(height: 12),
        OutlinedButton(onPressed: retry, child: const Text('Reintentar')),
      ],
    ),
  ),
);
