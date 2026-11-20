import 'package:flutter/material.dart';

import '../../../core/network/api_client.dart';

class PatientPortalError extends StatelessWidget {
  const PatientPortalError({
    super.key,
    required this.error,
    required this.onRetry,
  });

  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final code = apiErrorCode(error);
    final (icon, title) = switch (code) {
      'paciente_no_vinculado' => (
        Icons.link_off_outlined,
        'Cuenta pendiente de vinculación',
      ),
      'paciente_inactivo' => (Icons.person_off_outlined, 'Expediente inactivo'),
      'historia_no_disponible' => (
        Icons.medical_information_outlined,
        'Historia clínica no disponible',
      ),
      _ => (Icons.cloud_off_outlined, 'No se pudo cargar la información'),
    };
    final message = apiErrorMessage(error);

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 44,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 12),
              Text(
                title,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              OutlinedButton(
                onPressed: onRetry,
                child: const Text('Reintentar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
