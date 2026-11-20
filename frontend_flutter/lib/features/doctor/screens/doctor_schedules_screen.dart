import 'package:flutter/material.dart';

import '../../../core/network/api_client.dart';
import '../data/doctor_api.dart';
import '../doctor_theme.dart';

class DoctorSchedulesScreen extends StatefulWidget {
  const DoctorSchedulesScreen({super.key, required this.api});
  final DoctorApi api;

  @override
  State<DoctorSchedulesScreen> createState() => _DoctorSchedulesScreenState();
}

class _DoctorSchedulesScreenState extends State<DoctorSchedulesScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.api.schedules();
  }

  void _reload() {
    final future = widget.api.schedules();
    setState(() => _future = future);
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(17, 8, 17, 13),
        child: Row(
          children: [
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Mis horarios',
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      color: DoctorColors.text,
                    ),
                  ),
                  SizedBox(height: 3),
                  Text(
                    'Configura tu disponibilidad semanal.',
                    style: TextStyle(color: DoctorColors.muted, fontSize: 12),
                  ),
                ],
              ),
            ),
            FilledButton.icon(
              onPressed: () => _editSchedule(),
              icon: const Icon(Icons.add_rounded, size: 18),
              label: const Text('Crear horario'),
              style: FilledButton.styleFrom(
                backgroundColor: DoctorColors.darkTeal,
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 11,
                ),
                textStyle: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ],
        ),
      ),
      Expanded(
        child: FutureBuilder<List<Map<String, dynamic>>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return _ErrorState(error: snapshot.error!, onRetry: _reload);
            }
            final schedules = [
              ...snapshot.data ?? const <Map<String, dynamic>>[],
            ];
            schedules.sort((a, b) {
              final weekday = (a['dia_semana'] as num? ?? 0).compareTo(
                b['dia_semana'] as num? ?? 0,
              );
              return weekday != 0
                  ? weekday
                  : '${a['hora_inicio']}'.compareTo('${b['hora_inicio']}');
            });
            if (schedules.isEmpty) {
              return RefreshIndicator(
                onRefresh: () async {
                  final future = widget.api.schedules();
                  setState(() => _future = future);
                  try {
                    await future;
                  } catch (_) {}
                },
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  children: const [
                    SizedBox(height: 145),
                    Icon(
                      Icons.schedule_outlined,
                      size: 42,
                      color: DoctorColors.teal,
                    ),
                    SizedBox(height: 12),
                    Center(
                      child: Text(
                        'Todavía no registraste horarios.',
                        style: TextStyle(color: DoctorColors.muted),
                      ),
                    ),
                    SizedBox(height: 5),
                    Center(
                      child: Text(
                        'Usa “Crear horario” para agregar disponibilidad.',
                        style: TextStyle(
                          color: DoctorColors.muted,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }
            return RefreshIndicator(
              onRefresh: () async {
                final future = widget.api.schedules();
                setState(() => _future = future);
                try {
                  await future;
                } catch (_) {}
              },
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 22),
                itemCount: schedules.length,
                separatorBuilder: (context, index) => const SizedBox(height: 8),
                itemBuilder: (context, index) => _ScheduleCard(
                  schedule: schedules[index],
                  onEdit: () => _editSchedule(schedule: schedules[index]),
                  onDelete: () => _confirmDelete(schedules[index]),
                ),
              ),
            );
          },
        ),
      ),
    ],
  );

  Future<void> _editSchedule({Map<String, dynamic>? schedule}) async {
    final result = await showDialog<_ScheduleInput>(
      context: context,
      builder: (_) => _ScheduleDialog(schedule: schedule),
    );
    if (result == null || !mounted) return;
    try {
      if (schedule == null) {
        await widget.api.createSchedule(
          weekday: result.weekday,
          start: result.start,
          end: result.end,
        );
      } else {
        final id = (schedule['id'] as num).toInt();
        await widget.api.updateSchedule(
          id,
          weekday: result.weekday,
          start: result.start,
          end: result.end,
        );
      }
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            schedule == null ? 'Horario creado.' : 'Horario actualizado.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
    }
  }

  Future<void> _confirmDelete(Map<String, dynamic> schedule) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Eliminar horario'),
        content: Text(
          '¿Quieres eliminar el horario del ${_weekdayName(schedule['dia_semana'])}?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (confirm != true || !mounted) return;
    try {
      await widget.api.deleteSchedule((schedule['id'] as num).toInt());
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Horario eliminado.')));
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
    }
  }
}

class _ScheduleCard extends StatelessWidget {
  const _ScheduleCard({
    required this.schedule,
    required this.onEdit,
    required this.onDelete,
  });
  final Map<String, dynamic> schedule;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 11),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: DoctorColors.soft,
              borderRadius: BorderRadius.circular(12),
            ),
            alignment: Alignment.center,
            child: Text(
              _shortWeekday(schedule['dia_semana']),
              style: const TextStyle(
                color: DoctorColors.teal,
                fontWeight: FontWeight.w800,
                fontSize: 11,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${_time(schedule['hora_inicio'])} - ${_time(schedule['hora_fin'])}',
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  schedule['medico_nombre']?.toString() ??
                      'Horario de atención',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: DoctorColors.muted,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Editar horario',
            onPressed: onEdit,
            icon: const Icon(
              Icons.edit_outlined,
              size: 19,
              color: DoctorColors.muted,
            ),
          ),
          IconButton(
            tooltip: 'Eliminar horario',
            onPressed: onDelete,
            icon: const Icon(
              Icons.delete_outline_rounded,
              size: 19,
              color: DoctorColors.muted,
            ),
          ),
        ],
      ),
    ),
  );
}

class _ScheduleInput {
  const _ScheduleInput(this.weekday, this.start, this.end);
  final int weekday;
  final String start;
  final String end;
}

class _ScheduleDialog extends StatefulWidget {
  const _ScheduleDialog({this.schedule});
  final Map<String, dynamic>? schedule;

  @override
  State<_ScheduleDialog> createState() => _ScheduleDialogState();
}

class _ScheduleDialogState extends State<_ScheduleDialog> {
  late int _weekday;
  late TimeOfDay _start;
  late TimeOfDay _end;
  String? _validationError;

  @override
  void initState() {
    super.initState();
    final schedule = widget.schedule;
    _weekday = (schedule?['dia_semana'] as num?)?.toInt() ?? 0;
    _start =
        _parseTime(schedule?['hora_inicio']) ??
        const TimeOfDay(hour: 8, minute: 0);
    _end =
        _parseTime(schedule?['hora_fin']) ??
        const TimeOfDay(hour: 9, minute: 0);
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(widget.schedule == null ? 'Crear horario' : 'Editar horario'),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<int>(
          initialValue: _weekday,
          decoration: const InputDecoration(labelText: 'Día'),
          items: List.generate(
            7,
            (index) => DropdownMenuItem(
              value: index,
              child: Text(_weekdayName(index)),
            ),
          ),
          onChanged: (value) {
            if (value != null) setState(() => _weekday = value);
          },
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _timePicker(
                context,
                'Inicio',
                _start,
                (value) => setState(() => _start = value),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _timePicker(
                context,
                'Fin',
                _end,
                (value) => setState(() => _end = value),
              ),
            ),
          ],
        ),
        if (_validationError != null) ...[
          const SizedBox(height: 9),
          Text(
            _validationError!,
            style: const TextStyle(color: DoctorColors.red, fontSize: 12),
          ),
        ],
      ],
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancelar'),
      ),
      FilledButton(onPressed: _save, child: const Text('Guardar')),
    ],
  );

  Widget _timePicker(
    BuildContext context,
    String label,
    TimeOfDay value,
    ValueChanged<TimeOfDay> onChanged,
  ) => OutlinedButton(
    onPressed: () async {
      final picked = await showTimePicker(context: context, initialTime: value);
      if (picked != null) onChanged(picked);
    },
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 10, color: DoctorColors.muted),
        ),
        Text(
          value.format(context),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ],
    ),
  );

  void _save() {
    final startMinutes = _start.hour * 60 + _start.minute;
    final endMinutes = _end.hour * 60 + _end.minute;
    if (startMinutes >= endMinutes) {
      setState(
        () => _validationError = 'La hora de fin debe ser posterior al inicio.',
      );
      return;
    }
    Navigator.pop(
      context,
      _ScheduleInput(_weekday, _formatTime(_start), _formatTime(_end)),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});
  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.cloud_off_outlined,
            size: 38,
            color: DoctorColors.muted,
          ),
          const SizedBox(height: 10),
          Text(apiErrorMessage(error), textAlign: TextAlign.center),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: const Text('Reintentar')),
        ],
      ),
    ),
  );
}

String _weekdayName(dynamic value) {
  const days = [
    'Lunes',
    'Martes',
    'Miércoles',
    'Jueves',
    'Viernes',
    'Sábado',
    'Domingo',
  ];
  final index = value is num ? value.toInt() : int.tryParse('$value') ?? 0;
  return index >= 0 && index < days.length ? days[index] : 'Día';
}

String _shortWeekday(dynamic value) => _weekdayName(value).substring(0, 3);

String _time(dynamic value) =>
    value?.toString().split(':').take(2).join(':') ?? '--:--';

String _formatTime(TimeOfDay value) =>
    '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';

TimeOfDay? _parseTime(dynamic value) {
  final parts = value?.toString().split(':') ?? const <String>[];
  if (parts.length < 2) return null;
  final hour = int.tryParse(parts[0]);
  final minute = int.tryParse(parts[1]);
  if (hour == null || minute == null) return null;
  return TimeOfDay(hour: hour, minute: minute);
}
