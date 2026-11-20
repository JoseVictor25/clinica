import 'package:flutter/material.dart';

import '../../../core/models/page_result.dart';
import '../../../core/network/api_client.dart';
import '../clinic_theme.dart';
import '../data/patient_api.dart';
import '../widgets/patient_portal_error.dart';

class PatientConsultationsScreen extends StatefulWidget {
  const PatientConsultationsScreen({super.key, required this.api});
  final PatientApi api;

  @override
  State<PatientConsultationsScreen> createState() =>
      _PatientConsultationsScreenState();
}

class _PatientConsultationsScreenState
    extends State<PatientConsultationsScreen> {
  int _page = 1;
  late Future<PageResult> _future;
  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final future = widget.api.consultations(page: _page);
    setState(() {
      _future = future;
    });
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<PageResult>(
    future: _future,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return PatientPortalError(error: snapshot.error!, onRetry: _reload);
      }
      final page = snapshot.data!;
      return RefreshIndicator(
        onRefresh: () async => _reload(),
        child: ListView.builder(
          padding: const EdgeInsets.fromLTRB(18, 10, 18, 20),
          itemCount: page.results.length + 2,
          itemBuilder: (context, index) {
            if (index == 0) return _consultationsHeader(context);
            if (page.results.isEmpty && index == 1) {
              return const Padding(
                padding: EdgeInsets.only(top: 32),
                child: Center(child: Text('No hay consultas registradas.')),
              );
            }
            if (index == page.results.length + 1) {
              final maxPage = (page.count / 10).ceil();
              return Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    onPressed: _page > 1
                        ? () {
                            setState(() {
                              _page--;
                            });
                            _reload();
                          }
                        : null,
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Text('Página $_page${maxPage > 0 ? ' de $maxPage' : ''}'),
                  IconButton(
                    onPressed: _page * 10 < page.count
                        ? () {
                            setState(() {
                              _page++;
                            });
                            _reload();
                          }
                        : null,
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
              );
            }
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _consultationCard(context, page.results[index - 1]),
            );
          },
        ),
      );
    },
  );
}

Widget _consultationsHeader(BuildContext context) => Padding(
  padding: const EdgeInsets.only(bottom: 14),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Consultas y recetas',
        style: Theme.of(context).textTheme.titleLarge
            ?.copyWith(fontWeight: FontWeight.w800, color: ClinicColors.text),
      ),
      const SizedBox(height: 3),
      const Text(
        'Revisa tus diagnósticos, indicaciones y recetas.',
        style: TextStyle(color: ClinicColors.muted, fontSize: 13),
      ),
    ],
  ),
);

Widget _consultationCard(
  BuildContext context,
  Map<String, dynamic> consultation,
) {
  final doctor = consultation['medico'] is Map
      ? Map<String, dynamic>.from(consultation['medico'] as Map)
      : <String, dynamic>{};
  final prescriptions = (consultation['recetas'] as List? ?? const [])
      .whereType<Map>()
      .toList();
  final studies = (consultation['estudios_medicos'] as List? ?? const [])
      .whereType<Map>()
      .toList();
  return Card(
    child: Padding(
      padding: const EdgeInsets.all(17),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: ClinicColors.soft,
                  borderRadius: BorderRadius.circular(13),
                ),
                child: const Icon(
                  Icons.assignment_outlined,
                  color: ClinicColors.primary,
                ),
              ),
              const SizedBox(width: 11),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _dateOnly(consultation['fecha']),
                      style: Theme.of(context).textTheme.titleSmall
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    Text(
                      doctor['especialidad']?.toString() ?? 'Consulta médica',
                      style: const TextStyle(
                        color: ClinicColors.muted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(
                Icons.check_circle_outline,
                color: ClinicColors.primary,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            doctor['nombre']?.toString() ?? 'Médico',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              color: ClinicColors.soft,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'MOTIVO / DIAGNÓSTICO',
                  style: TextStyle(
                    color: ClinicColors.primary,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 5),
                _textField('Motivo', consultation['motivo']),
                _textField('Diagnóstico', consultation['diagnostico']),
                if (consultation['observacion']?.toString().isNotEmpty == true)
                  _textField('Observación', consultation['observacion']),
              ],
            ),
          ),
          const Divider(),
          Text(
            'Recetas (${prescriptions.length})',
            style: Theme.of(context).textTheme.titleSmall,
          ),
          if (prescriptions.isEmpty) const Text('Sin recetas.'),
          for (final prescription in prescriptions)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(
                'Receta #${prescription['id']} · ${prescription['cantidad_medicamentos'] ?? 0} medicamento(s)',
              ),
              subtitle: Text(
                prescription['indicaciones']?.toString().isNotEmpty == true
                    ? prescription['indicaciones'].toString()
                    : 'Sin indicaciones generales',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => _showPrescription(
                context,
                (prescription['id'] as num).toInt(),
                _apiFromCard(context),
              ),
            ),
          if (studies.isNotEmpty) ...[
            const Divider(),
            Text(
              'Estudios médicos (${studies.length})',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            for (final study in studies)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.monitor_heart_outlined),
                title: Text(study['nombre_archivo']?.toString() ?? 'Estudio'),
                subtitle: Text(
                  '${study['tipo_estudio_display'] ?? ''} · ${study['estado_display'] ?? ''}${study['observacion_lectura'] == null ? '' : '\n${study['observacion_lectura']}'}',
                ),
              ),
          ],
        ],
      ),
    ),
  );
}

String _dateOnly(dynamic value) {
  final text = value?.toString() ?? '';
  if (text.isEmpty) return 'Consulta médica';
  return text.split('T').first;
}

Widget _textField(String label, dynamic value) => Padding(
  padding: const EdgeInsets.only(top: 6),
  child: Text('$label: ${value?.toString().isNotEmpty == true ? value : '—'}'),
);

PatientApi _apiFromCard(BuildContext context) =>
    (context.findAncestorStateOfType<_PatientConsultationsScreenState>()!)
        .widget
        .api;

Future<void> _showPrescription(
  BuildContext context,
  int id,
  PatientApi api,
) async {
  try {
    final data = await api.prescription(id);
    if (!context.mounted) return;
    final doctor = data['medico'] is Map
        ? Map<String, dynamic>.from(data['medico'] as Map)
        : <String, dynamic>{};
    final medicines = (data['medicamentos'] as List? ?? const [])
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
                'Detalle de receta #$id',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              Text('Fecha: ${data['fecha'] ?? '—'}'),
              Text(
                'Médico: ${doctor['nombre'] ?? '—'} · ${doctor['especialidad'] ?? ''}',
              ),
              Text(
                'Indicaciones: ${data['indicaciones']?.toString().isNotEmpty == true ? data['indicaciones'] : 'Sin indicaciones generales'}',
              ),
              const Divider(),
              const Text(
                'Medicamentos',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              for (final medicine in medicines)
                Card(
                  child: ListTile(
                    title: Text(
                      medicine['nombre_medicamento']?.toString() ?? '',
                    ),
                    subtitle: Text(
                      'Dosis: ${medicine['dosis'] ?? '—'}\nFrecuencia: ${medicine['frecuencia'] ?? '—'}\nDuración: ${medicine['duracion'] ?? '—'}',
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  } catch (error) {
    if (context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
    }
  }
}
