import 'package:flutter/material.dart';

import '../../../core/network/api_client.dart';
import '../data/doctor_api.dart';

class _MedicineFields {
  final name = TextEditingController();
  final dose = TextEditingController();
  final frequency = TextEditingController();
  final duration = TextEditingController();
  void dispose() {
    name.dispose();
    dose.dispose();
    frequency.dispose();
    duration.dispose();
  }
}

class DoctorPrescriptionFormScreen extends StatefulWidget {
  const DoctorPrescriptionFormScreen({
    super.key,
    required this.api,
    required this.consultationId,
  });
  final DoctorApi api;
  final int consultationId;

  @override
  State<DoctorPrescriptionFormScreen> createState() =>
      _DoctorPrescriptionFormScreenState();
}

class _DoctorPrescriptionFormScreenState
    extends State<DoctorPrescriptionFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _instructions = TextEditingController();
  final List<_MedicineFields> _medicines = [_MedicineFields()];
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _instructions.dispose();
    for (final medicine in _medicines) {
      medicine.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final medicines = _medicines
          .map(
            (medicine) => {
              'nombre_medicamento': medicine.name.text.trim(),
              'dosis': medicine.dose.text.trim(),
              'frecuencia': medicine.frequency.text.trim(),
              'duracion': medicine.duration.text.trim(),
            },
          )
          .toList();
      await widget.api.createPrescription(
        widget.consultationId,
        instructions: _instructions.text.trim(),
        medicines: medicines,
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
    appBar: AppBar(title: const Text('Emitir receta')),
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextFormField(
            controller: _instructions,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Indicaciones generales',
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Text(
                  'Medicamentos',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              IconButton(
                onPressed: () =>
                    setState(() => _medicines.add(_MedicineFields())),
                icon: const Icon(Icons.add_circle_outline),
                tooltip: 'Agregar medicamento',
              ),
            ],
          ),
          for (var index = 0; index < _medicines.length; index++)
            _medicineCard(index),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: _saving ? null : _submit,
            icon: _saving
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.receipt_long),
            label: const Text('Emitir receta'),
          ),
        ],
      ),
    ),
  );

  Widget _medicineCard(int index) {
    final fields = _medicines[index];
    return Card(
      margin: const EdgeInsets.only(top: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Medicamento ${index + 1}',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
                if (_medicines.length > 1)
                  IconButton(
                    onPressed: () => setState(() {
                      _medicines.removeAt(index).dispose();
                    }),
                    icon: const Icon(Icons.delete_outline),
                    tooltip: 'Quitar',
                  ),
              ],
            ),
            TextFormField(
              controller: fields.name,
              decoration: const InputDecoration(labelText: 'Nombre'),
              validator: _required,
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: fields.dose,
              decoration: const InputDecoration(labelText: 'Dosis'),
              validator: _required,
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: fields.frequency,
              decoration: const InputDecoration(labelText: 'Frecuencia'),
              validator: _required,
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: fields.duration,
              decoration: const InputDecoration(labelText: 'Duración'),
              validator: _required,
            ),
          ],
        ),
      ),
    );
  }
}

String? _required(String? value) {
  if (value == null || value.trim().isEmpty) {
    return 'Este campo es obligatorio.';
  }
  if (value.trim().length > 150) {
    return 'El texto excede la longitud permitida.';
  }
  return null;
}
