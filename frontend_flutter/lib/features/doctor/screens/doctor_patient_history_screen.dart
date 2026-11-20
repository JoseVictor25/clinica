import 'package:flutter/material.dart';

import '../../../core/network/api_client.dart';
import '../data/doctor_api.dart';

class DoctorPatientHistoryScreen extends StatefulWidget {
  const DoctorPatientHistoryScreen({
    super.key,
    required this.api,
    required this.patientId,
    required this.patientName,
  });
  final DoctorApi api;
  final int patientId;
  final String patientName;

  @override
  State<DoctorPatientHistoryScreen> createState() =>
      _DoctorPatientHistoryScreenState();
}

class _DoctorPatientHistoryScreenState
    extends State<DoctorPatientHistoryScreen> {
  int _page = 1;
  late Future<Map<String, dynamic>> _future;
  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = widget.api.patientHistory(widget.patientId, page: _page);
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Historial de consultas')),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) return _error(context, snapshot.error!, _reload);
        final data = snapshot.data!;
        final patient = data['paciente'] is Map
            ? Map<String, dynamic>.from(data['paciente'] as Map)
            : <String, dynamic>{};
        final results = (data['results'] as List? ?? const [])
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e))
            .toList();
        final count = (data['count'] as num? ?? 0).toInt();
        if (results.isEmpty) {
          return const Center(child: Text('No hay consultas en el historial.'));
        }
        return RefreshIndicator(
          onRefresh: () async => _reload(),
          child: ListView(
            padding: const EdgeInsets.all(12),
            children: [
              Card(
                child: ListTile(
                  title: Text(
                    '${patient['apellido'] ?? ''}, ${patient['nombre'] ?? widget.patientName}',
                  ),
                  subtitle: Text('CI ${patient['ci'] ?? '—'}'),
                ),
              ),
              for (final consultation in results)
                _historyCard(context, consultation),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    onPressed: _page > 1
                        ? () => setState(() {
                            _page--;
                            _reload();
                          })
                        : null,
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Text('Página $_page'),
                  IconButton(
                    onPressed: _page * 10 < count
                        ? () => setState(() {
                            _page++;
                            _reload();
                          })
                        : null,
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    ),
  );
}

Widget _historyCard(BuildContext context, Map<String, dynamic> item) {
  final doctor = item['medico'] is Map
      ? Map<String, dynamic>.from(item['medico'] as Map)
      : <String, dynamic>{};
  final recipes = (item['recetas'] as List? ?? const [])
      .whereType<Map>()
      .toList();
  final studies = (item['estudios_medicos'] as List? ?? const [])
      .whereType<Map>()
      .toList();
  return Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Consulta · ${item['fecha'] ?? ''}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text(
            'Médico: ${doctor['nombre'] ?? '—'} · ${doctor['especialidad'] ?? ''}',
          ),
          _field('Motivo', item['motivo']),
          _field('Diagnóstico', item['diagnostico']),
          _field('Observación', item['observacion']),
          const Divider(),
          Text(
            'Recetas (${recipes.length})',
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          for (final recipe in recipes)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'Receta #${recipe['id']} · ${recipe['indicaciones'] ?? 'Sin indicaciones'} · ${recipe['medicamentos'] is List ? (recipe['medicamentos'] as List).length : 0} medicamento(s)',
              ),
            ),
          if (studies.isNotEmpty) ...[
            const Divider(),
            Text(
              'Estudios (${studies.length})',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            for (final study in studies)
              Text(
                '${study['nombre_archivo'] ?? ''} · ${study['tipo_estudio_display'] ?? ''} · ${study['estado_display'] ?? ''}',
              ),
          ],
        ],
      ),
    ),
  );
}

Widget _field(String label, dynamic value) => Padding(
  padding: const EdgeInsets.only(top: 6),
  child: Text('$label: ${value?.toString().isNotEmpty == true ? value : '—'}'),
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
