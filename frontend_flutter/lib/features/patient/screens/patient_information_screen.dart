import 'package:flutter/material.dart';

import '../clinic_theme.dart';
import '../data/patient_api.dart';
import '../widgets/patient_portal_error.dart';

class PatientInformationScreen extends StatefulWidget {
  const PatientInformationScreen({super.key, required this.api});
  final PatientApi api;

  @override
  State<PatientInformationScreen> createState() =>
      _PatientInformationScreenState();
}

class _PatientInformationScreenState extends State<PatientInformationScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.api.myInformation();
  }

  void _reload() {
    final future = widget.api.myInformation();
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
      return ListView(
        padding: const EdgeInsets.fromLTRB(18, 10, 18, 24),
        children: [
          Text(
            'Información del paciente',
            style: Theme.of(context).textTheme.titleMedium
                ?.copyWith(color: ClinicColors.muted),
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        radius: 26,
                        backgroundColor: ClinicColors.primary,
                        foregroundColor: Colors.white,
                        child: Text(
                          (data['nombre']?.toString().trim().isNotEmpty == true
                                  ? data['nombre'].toString().trim()[0]
                                  : 'P')
                              .toUpperCase(),
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${data['nombre'] ?? ''} ${data['apellido'] ?? ''}',
                              style: Theme.of(context).textTheme.titleLarge
                                  ?.copyWith(fontWeight: FontWeight.w800),
                            ),
                            const SizedBox(height: 3),
                            const Text(
                              'Información del paciente',
                              style: TextStyle(color: ClinicColors.muted),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  _field('Cédula de identidad', data['ci']),
                  _field('Fecha de nacimiento', data['fecha_nacimiento']),
                  _field('Sexo biológico', data['sexo']),
                  _field('Teléfono', data['telefono']),
                  _field(
                    'Correo electrónico',
                    (data['email'] as String?)?.isNotEmpty == true
                        ? data['email']
                        : 'Sin correo registrado',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          const Card(
            child: Padding(
              padding: EdgeInsets.all(14),
              child: Row(
                children: [
                  Icon(Icons.lock_outline, size: 18, color: ClinicColors.muted),
                  SizedBox(width: 9),
                  Expanded(
                    child: Text(
                      'Ficha protegida · Solo lectura',
                      style: TextStyle(color: ClinicColors.muted, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      );
    },
  );
}

Widget _field(String label, dynamic value) => Padding(
  padding: const EdgeInsets.only(bottom: 12),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: const TextStyle(color: ClinicColors.muted, fontSize: 12),
      ),
      const SizedBox(height: 4),
      Text(
        value?.toString() ?? '—',
        style: const TextStyle(fontWeight: FontWeight.w600),
      ),
      const SizedBox(height: 10),
      const Divider(height: 1, color: ClinicColors.border),
    ],
  ),
);
