import 'package:flutter/material.dart';

class RoleSelectionScreen extends StatelessWidget {
  const RoleSelectionScreen({
    super.key,
    required this.username,
    required this.onSelectDoctor,
    required this.onSelectPatient,
  });

  final String username;
  final VoidCallback onSelectDoctor;
  final VoidCallback onSelectPatient;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Clínica')),
    body: Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(
                Icons.local_hospital_rounded,
                size: 54,
                color: Color(0xff087e8b),
              ),
              const SizedBox(height: 16),
              Text(
                'Hola, $username',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                '¿Cómo quieres ingresar?',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: onSelectDoctor,
                icon: const Icon(Icons.medical_services_outlined),
                label: const Padding(
                  padding: EdgeInsets.symmetric(vertical: 14),
                  child: Text('Continuar como médico'),
                ),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: onSelectPatient,
                icon: const Icon(Icons.person_outline),
                label: const Padding(
                  padding: EdgeInsets.symmetric(vertical: 14),
                  child: Text('Continuar como paciente'),
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
