import 'package:flutter/material.dart';

import '../clinic_theme.dart';
import '../data/patient_api.dart';
import '../widgets/patient_portal_error.dart';

class PatientHistoryScreen extends StatefulWidget {
  const PatientHistoryScreen({super.key, required this.api});
  final PatientApi api;

  @override
  State<PatientHistoryScreen> createState() => _PatientHistoryScreenState();
}

class _PatientHistoryScreenState extends State<PatientHistoryScreen> {
  late Future<Map<String, dynamic>> _future;
  @override
  void initState() {
    super.initState();
    _future = widget.api.myHistory();
  }

  void _reload() {
    final future = widget.api.myHistory();
    setState(() {
      _future = future;
    });
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>>(
    future: _future,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return PatientPortalError(error: snapshot.error!, onRetry: _reload);
      }
      final data = snapshot.data!;
      final diseases = (data['enfermedades'] as List? ?? const [])
          .whereType<Map>()
          .toList();
      final allergies = (data['alergias'] as List? ?? const [])
          .whereType<Map>()
          .toList();
      return RefreshIndicator(
        onRefresh: () async => _reload(),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 10, 18, 24),
          children: [
            Text(
              'Expediente clínico',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: ClinicColors.text,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(17),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(
                          Icons.folder_open_outlined,
                          color: ClinicColors.primary,
                        ),
                        const SizedBox(width: 9),
                        const Expanded(
                          child: Text(
                            'Expediente del paciente',
                            style: TextStyle(fontWeight: FontWeight.w800),
                          ),
                        ),
                        _statusBadge(
                          data['estado'] == true ? 'Activo' : 'Inactivo',
                        ),
                      ],
                    ),
                    const SizedBox(height: 15),
                    _field('Fecha de apertura', data['fecha_apertura']),
                    _field('Grupo sanguíneo', data['grupo_sanguineo']),
                    _field(
                      'Observaciones',
                      (data['observaciones_generales'] as String?)
                                  ?.isNotEmpty ==
                              true
                          ? data['observaciones_generales']
                          : 'Sin observaciones',
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            _listSection(
              context,
              'Enfermedades',
              diseases,
              (item) =>
                  '${item['nombre'] ?? ''} · ${item['tipo'] ?? ''} · ${item['severidad'] ?? ''} · ${item['fecha_deteccion'] ?? ''}',
            ),
            const SizedBox(height: 12),
            _listSection(
              context,
              'Alergias',
              allergies,
              (item) =>
                  '${item['nombre'] ?? ''} · ${item['tipo'] ?? ''} · ${item['severidad'] ?? ''}${item['descripcion'] == null || item['descripcion'] == '' ? '' : ' · ${item['descripcion']}'}',
            ),
          ],
        ),
      );
    },
  );
}

Widget _listSection(
  BuildContext context,
  String title,
  List<Map> items,
  String Function(Map) text,
) => Card(
  child: Padding(
    padding: const EdgeInsets.all(17),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              title == 'Enfermedades'
                  ? Icons.health_and_safety_outlined
                  : Icons.shield_outlined,
              color: ClinicColors.primary,
              size: 20,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                title,
                style: Theme.of(context).textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
            ),
            _statusBadge('Actual'),
          ],
        ),
        const SizedBox(height: 8),
        if (items.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              color: ClinicColors.soft,
              borderRadius: BorderRadius.circular(13),
            ),
            child: Text('Sin ${title.toLowerCase()} registradas actualmente.'),
          ),
        for (final item in items)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.circle, size: 9),
            title: Text(text(item)),
          ),
      ],
    ),
  ),
);

Widget _statusBadge(String label) => Container(
  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
  decoration: BoxDecoration(
    color: ClinicColors.mint,
    borderRadius: BorderRadius.circular(20),
  ),
  child: Text(
    label,
    style: const TextStyle(
      color: ClinicColors.dark,
      fontSize: 10,
      fontWeight: FontWeight.w700,
    ),
  ),
);

Widget _field(String label, dynamic value) => Padding(
  padding: const EdgeInsets.only(bottom: 12),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: const TextStyle(color: ClinicColors.muted, fontSize: 12),
      ),
      const SizedBox(height: 2),
      Text(
        value?.toString() ?? '—',
        style: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ],
  ),
);
