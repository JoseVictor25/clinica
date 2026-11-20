import 'package:flutter/material.dart';

import '../../../core/network/api_client.dart';
import '../data/doctor_api.dart';

class DoctorConsultationFormScreen extends StatefulWidget {
  const DoctorConsultationFormScreen({
    super.key,
    required this.api,
    required this.appointment,
  });
  final DoctorApi api;
  final Map<String, dynamic> appointment;

  @override
  State<DoctorConsultationFormScreen> createState() =>
      _DoctorConsultationFormScreenState();
}

class _DoctorConsultationFormScreenState
    extends State<DoctorConsultationFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final _reason = TextEditingController(
    text: widget.appointment['motivo']?.toString() ?? '',
  );
  final _notes = TextEditingController();
  final _diagnosis = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _reason.dispose();
    _notes.dispose();
    _diagnosis.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await widget.api.createConsultation(
        appointmentId: (widget.appointment['id'] as num).toInt(),
        reason: _reason.text.trim(),
        notes: _notes.text.trim(),
        diagnosis: _diagnosis.text.trim(),
      );
      if (mounted) Navigator.of(context).pop(true);
    } catch (error) {
      setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Registrar consulta')),
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Paciente: ${widget.appointment['paciente_nombre'] ?? '—'}',
                  ),
                  Text(
                    'Cita: ${widget.appointment['fecha'] ?? ''} · ${widget.appointment['hora'] ?? ''}',
                  ),
                  Text(
                    'Especialidad: ${widget.appointment['especialidad_nombre'] ?? '—'}',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          TextFormField(
            controller: _reason,
            maxLines: 2,
            decoration: const InputDecoration(labelText: 'Motivo de consulta'),
            validator: _required,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _notes,
            maxLines: 4,
            decoration: const InputDecoration(labelText: 'Observación'),
            validator: _required,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _diagnosis,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'Diagnóstico'),
            validator: _required,
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: _saving ? null : _submit,
            icon: _saving
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save_outlined),
            label: const Text('Registrar consulta'),
          ),
        ],
      ),
    ),
  );
}

String? _required(String? value) =>
    value == null || value.trim().isEmpty ? 'Este campo es obligatorio.' : null;
