import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/models/page_result.dart';
import '../../../core/network/api_client.dart';
import '../../../core/session/session_controller.dart';
import '../data/doctor_api.dart';
import '../doctor_theme.dart';
import 'doctor_consultation_detail_screen.dart';
import 'doctor_consultation_form_screen.dart';
import 'doctor_patient_history_screen.dart';
import '../../shared/telemedicine_call_screen.dart';

class DoctorAgendaScreen extends StatefulWidget {
  const DoctorAgendaScreen({
    super.key,
    required this.api,
    required this.session,
  });

  final DoctorApi api;
  final SessionController session;

  @override
  State<DoctorAgendaScreen> createState() => _DoctorAgendaScreenState();
}

class _DoctorAgendaScreenState extends State<DoctorAgendaScreen> {
  DateTime _date = DateUtils.dateOnly(DateTime.now());
  int _filter = 0;
  late Future<PageResult> _future;

  String get _dateString => DateFormat('yyyy-MM-dd').format(_date);

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<PageResult> _load() => widget.api.agenda(date: _dateString);

  void _reload() {
    final future = _load();
    setState(() => _future = future);
  }

  void _changeDay(int amount) {
    setState(() {
      _date = DateUtils.dateOnly(_date.add(Duration(days: amount)));
      _filter = 0;
      _future = _load();
    });
  }

  Future<void> _pickDate() async {
    final selected = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
      helpText: 'Selecciona el día de la agenda',
    );
    if (selected == null || !mounted) return;
    setState(() {
      _date = DateUtils.dateOnly(selected);
      _filter = 0;
      _future = _load();
    });
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(17, 8, 17, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Mi agenda',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: DoctorColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (DateUtils.isSameDay(_date, DateTime.now()))
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 11,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: DoctorColors.mint,
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: const Text(
                      'Hoy',
                      style: TextStyle(
                        color: DoctorColors.teal,
                        fontWeight: FontWeight.w700,
                        fontSize: 11,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 13),
            Card(
              child: SizedBox(
                height: 48,
                child: Row(
                  children: [
                    IconButton(
                      tooltip: 'Día anterior',
                      onPressed: () => _changeDay(-1),
                      icon: const Icon(Icons.chevron_left_rounded),
                    ),
                    Expanded(
                      child: InkWell(
                        onTap: _pickDate,
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(
                              Icons.calendar_month_outlined,
                              size: 18,
                              color: DoctorColors.teal,
                            ),
                            const SizedBox(width: 8),
                            Flexible(
                              child: Text(
                                _longDate(_date),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: 'Día siguiente',
                      onPressed: () => _changeDay(1),
                      icon: const Icon(Icons.chevron_right_rounded),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            FutureBuilder<PageResult>(
              future: _future,
              builder: (context, snapshot) {
                final items =
                    snapshot.data?.results ?? const <Map<String, dynamic>>[];
                final pending = items.where(_isPending).length;
                final attended = items
                    .where((item) => item['estado'] == 'ATENDIDA')
                    .length;
                return SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _FilterChip(
                        label: 'Todas',
                        count: snapshot.data?.count ?? 0,
                        selected: _filter == 0,
                        onTap: () => setState(() => _filter = 0),
                      ),
                      const SizedBox(width: 7),
                      _FilterChip(
                        label: 'Pendientes',
                        count: pending,
                        selected: _filter == 1,
                        onTap: () => setState(() => _filter = 1),
                      ),
                      const SizedBox(width: 7),
                      _FilterChip(
                        label: 'Atendidas',
                        count: attended,
                        selected: _filter == 2,
                        onTap: () => setState(() => _filter = 2),
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
      Expanded(
        child: FutureBuilder<PageResult>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return _errorState(snapshot.error!, _reload);
            }
            final result = snapshot.data!;
            final items = result.results
                .where(
                  (item) => switch (_filter) {
                    1 => _isPending(item),
                    2 => item['estado'] == 'ATENDIDA',
                    _ => true,
                  },
                )
                .toList();
            if (items.isEmpty) {
              return RefreshIndicator(
                onRefresh: () async {
                  final future = _load();
                  setState(() => _future = future);
                  try {
                    await future;
                  } catch (_) {}
                },
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  children: [
                    SizedBox(height: 180),
                    Icon(
                      Icons.event_available_outlined,
                      size: 42,
                      color: DoctorColors.teal.withValues(alpha: .6),
                    ),
                    const SizedBox(height: 12),
                    Center(
                      child: Text(
                        _emptyMessage(),
                        style: const TextStyle(color: DoctorColors.muted),
                      ),
                    ),
                  ],
                ),
              );
            }
            return RefreshIndicator(
              onRefresh: () async {
                final future = _load();
                setState(() => _future = future);
                try {
                  await future;
                } catch (_) {}
              },
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(15, 2, 15, 20),
                itemCount: items.length,
                separatorBuilder: (context, index) => const SizedBox(height: 9),
                itemBuilder: (context, index) =>
                    _appointmentCard(context, items[index]),
              ),
            );
          },
        ),
      ),
    ],
  );

  Widget _appointmentCard(BuildContext context, Map<String, dynamic> item) {
    final state = item['estado']?.toString() ?? '';
    final attended = state == 'ATENDIDA';
    final historyId = item['paciente_id'] is num
        ? (item['paciente_id'] as num).toInt()
        : null;
    final consultationId = item['consulta_id'] is num
        ? (item['consulta_id'] as num).toInt()
        : null;
    final canAttend = state == 'CONFIRMADA' && item['tiene_consulta'] != true;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 49,
              height: 56,
              decoration: BoxDecoration(
                color: attended ? DoctorColors.lavender : DoctorColors.soft,
                borderRadius: BorderRadius.circular(13),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _time(item['hora']),
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const Text(
                    'hora',
                    style: TextStyle(fontSize: 9, color: DoctorColors.muted),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item['paciente_nombre']?.toString() ?? 'Paciente',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    item['especialidad_nombre']?.toString() ??
                        item['motivo']?.toString() ??
                        'Consulta médica',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: DoctorColors.muted,
                      fontSize: 11,
                    ),
                  ),
                  const SizedBox(height: 5),
                  _StateBadge(
                    label: item['estado_display']?.toString() ?? state,
                    state: state,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 6),
            if (canAttend)
              FilledButton.icon(
                onPressed: () => _openConsultation(item),
                icon: const Icon(Icons.medical_services_outlined, size: 15),
                label: const Text('Atender'),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 11,
                    vertical: 10,
                  ),
                  textStyle: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(11),
                  ),
                ),
              )
            else
              IconButton(
                tooltip: 'Ver detalle',
                onPressed: () => consultationId != null
                    ? _openConsultationDetail(consultationId)
                    : _showAppointment(item),
                icon: Icon(
                  consultationId != null
                      ? Icons.visibility_outlined
                      : Icons.chevron_right_rounded,
                  color: DoctorColors.teal,
                ),
              ),
            if (historyId != null)
              PopupMenuButton<String>(
                tooltip: 'Más acciones',
                onSelected: (value) {
                  if (value == 'history') {
                    _openHistory(
                      historyId,
                      item['paciente_nombre']?.toString() ?? 'Paciente',
                    );
                  } else if (value == 'detail') {
                    _showAppointment(item);
                  } else if (value == 'video') {
                    final link = item['link_videollamada']?.toString() ?? '';
                    if (link.isNotEmpty) {
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => TelemedicineCallScreen(
                            roomUrl: link,
                            displayName:
                                widget.session.profile?.username ?? 'Médico',
                            otherParticipantName:
                                item['paciente_nombre']?.toString() ??
                                'Paciente',
                          ),
                        ),
                      );
                    }
                  }
                },
                itemBuilder: (context) => [
                  const PopupMenuItem(
                    value: 'detail',
                    child: Text('Detalle de cita'),
                  ),
                  const PopupMenuItem(
                    value: 'history',
                    child: Text('Historia clínica'),
                  ),
                  if (item['modalidad'] == 'VIRTUAL' &&
                      (item['link_videollamada']?.toString().isNotEmpty ??
                          false) &&
                      state != 'CANCELADA' &&
                      state != 'NO_ASISTIO')
                    const PopupMenuItem(
                      value: 'video',
                      child: Text('Abrir sala virtual'),
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _showAppointment(Map<String, dynamic> item) =>
      showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        builder: (context) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Detalle de la cita',
                  style: Theme.of(context).textTheme.titleLarge
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 14),
                _detail('Paciente', item['paciente_nombre']),
                _detail('Fecha', item['fecha']),
                _detail('Hora', item['hora']),
                _detail('Estado', item['estado_display'] ?? item['estado']),
                _detail(
                  'Modalidad',
                  item['modalidad_display'] ?? item['modalidad'],
                ),
                _detail('Motivo', item['motivo']),
                _detail('Especialidad', item['especialidad_nombre']),
              ],
            ),
          ),
        ),
      );

  Future<void> _openConsultation(Map<String, dynamic> appointment) async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => DoctorConsultationFormScreen(
          api: widget.api,
          appointment: appointment,
        ),
      ),
    );
    if (saved == true && mounted) _reload();
  }

  Future<void> _openConsultationDetail(int id) => Navigator.of(context)
      .push<void>(
        MaterialPageRoute(
          builder: (_) => DoctorConsultationDetailScreen(
            api: widget.api,
            consultationId: id,
          ),
        ),
      );

  Future<void> _openHistory(int patientId, String name) =>
      Navigator.of(context).push<void>(
        MaterialPageRoute(
          builder: (_) => DoctorPatientHistoryScreen(
            api: widget.api,
            patientId: patientId,
            patientName: name,
          ),
        ),
      );

  bool _isPending(Map<String, dynamic> item) =>
      item['estado'] == 'PROGRAMADA' || item['estado'] == 'CONFIRMADA';

  String _emptyMessage() => switch (_filter) {
    1 => 'No hay citas pendientes para este día.',
    2 => 'Todavía no hay citas atendidas este día.',
    _ => 'No hay citas para esta fecha.',
  };
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.count,
    required this.selected,
    required this.onTap,
  });
  final String label;
  final int count;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ActionChip(
    onPressed: onTap,
    label: Text('$label ($count)'),
    labelStyle: TextStyle(
      color: selected ? Colors.white : DoctorColors.text,
      fontWeight: FontWeight.w700,
      fontSize: 11,
    ),
    backgroundColor: selected ? DoctorColors.teal : Colors.white,
    side: BorderSide(color: selected ? DoctorColors.teal : DoctorColors.border),
    shape: const StadiumBorder(),
    padding: const EdgeInsets.symmetric(horizontal: 3),
  );
}

class _StateBadge extends StatelessWidget {
  const _StateBadge({required this.label, required this.state});
  final String label;
  final String state;

  @override
  Widget build(BuildContext context) {
    final attended = state == 'ATENDIDA';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: attended ? DoctorColors.lavender : DoctorColors.soft,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 9,
          color: DoctorColors.darkTeal,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

Widget _detail(String title, dynamic value) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 4),
  child: Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      SizedBox(
        width: 95,
        child: Text(title, style: const TextStyle(color: DoctorColors.muted)),
      ),
      Expanded(
        child: Text(
          value?.toString() ?? '—',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
    ],
  ),
);

Widget _errorState(Object error, VoidCallback retry) => Center(
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
        OutlinedButton(onPressed: retry, child: const Text('Reintentar')),
      ],
    ),
  ),
);

String _time(dynamic value) =>
    value?.toString().split(':').take(2).join(':') ?? '--:--';

String _longDate(DateTime date) {
  const weekdays = [
    'lunes',
    'martes',
    'miércoles',
    'jueves',
    'viernes',
    'sábado',
    'domingo',
  ];
  const months = [
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'septiembre',
    'octubre',
    'noviembre',
    'diciembre',
  ];
  return '${weekdays[date.weekday - 1]}, ${date.day} de ${months[date.month - 1]} ${date.year}';
}
