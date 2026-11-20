import 'package:flutter/material.dart';

import '../../../core/models/page_result.dart';
import '../../../core/notifications/notification_inbox.dart';
import '../../../core/session/user_profile.dart';
import '../data/patient_api.dart';
import '../clinic_theme.dart';
import '../widgets/patient_portal_error.dart';

class PatientDashboardScreen extends StatefulWidget {
  const PatientDashboardScreen({
    super.key,
    required this.api,
    required this.inbox,
    required this.profile,
    required this.onOpenHistory,
    required this.onOpenAppointments,
    required this.onOpenConsultations,
  });

  final PatientApi api;
  final NotificationInboxController inbox;
  final UserProfile profile;
  final VoidCallback onOpenHistory;
  final VoidCallback onOpenAppointments;
  final VoidCallback onOpenConsultations;

  @override
  State<PatientDashboardScreen> createState() => _PatientDashboardScreenState();
}

class _DashboardData {
  const _DashboardData(this.patient, this.appointments);

  final Map<String, dynamic> patient;
  final PageResult appointments;
}

class _PatientDashboardScreenState extends State<PatientDashboardScreen> {
  late Future<_DashboardData> _future;
  late int _lastInboxRefresh;

  @override
  void initState() {
    super.initState();
    _future = _load();
    _lastInboxRefresh = widget.inbox.refreshVersion;
    widget.inbox.addListener(_onInboxChanged);
  }

  void _onInboxChanged() {
    if (!mounted || _lastInboxRefresh == widget.inbox.refreshVersion) return;
    _lastInboxRefresh = widget.inbox.refreshVersion;
    _reload();
  }

  @override
  void dispose() {
    widget.inbox.removeListener(_onInboxChanged);
    super.dispose();
  }

  Future<_DashboardData> _load() async {
    final patient = await widget.api.myInformation();
    final appointments = await widget.api.appointments();
    return _DashboardData(patient, appointments);
  }

  void _reload() {
    final future = _load();
    setState(() {
      _future = future;
    });
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<_DashboardData>(
    future: _future,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return PatientPortalError(error: snapshot.error!, onRetry: _reload);
      }

      final data = snapshot.data!;
      final firstName = _firstName(data.patient['nombre']);
      final nextAppointment = _nextAppointment(data.appointments.results);
      return RefreshIndicator(
        onRefresh: () async {
          final future = _load();
          setState(() {
            _future = future;
          });
          try {
            await future;
          } catch (_) {
            // FutureBuilder muestra el error y deja disponible Reintentar.
          }
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
          children: [
            Text(
              'Hola, $firstName 👋',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: ClinicColors.text,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Todo en orden con tu atención médica',
              style: Theme.of(context).textTheme.bodyMedium
                  ?.copyWith(color: ClinicColors.muted),
            ),
            const SizedBox(height: 20),
            _nextAppointmentCard(context, nextAppointment),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Accesos directos',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: ClinicColors.text,
                  ),
                ),
                const Text(
                  'Tu salud a mano',
                  style: TextStyle(fontSize: 12, color: ClinicColors.muted),
                ),
              ],
            ),
            const SizedBox(height: 10),
            _ShortcutCard(
              icon: Icons.medical_information_outlined,
              title: 'Historia clínica',
              subtitle: 'Enfermedades, alergias y ficha médica',
              onTap: widget.onOpenHistory,
            ),
            const SizedBox(height: 9),
            _ShortcutCard(
              icon: Icons.calendar_month_outlined,
              title: 'Citas médicas',
              subtitle: 'Revisa tus citas y horarios',
              onTap: widget.onOpenAppointments,
            ),
            const SizedBox(height: 9),
            _ShortcutCard(
              icon: Icons.assignment_outlined,
              title: 'Consultas y recetas',
              subtitle: 'Diagnósticos y prescripciones',
              onTap: widget.onOpenConsultations,
            ),
          ],
        ),
      );
    },
  );
}

String _firstName(dynamic value) {
  final name = value?.toString().trim() ?? '';
  return name.isEmpty ? 'Paciente' : name.split(RegExp(r'\s+')).first;
}

Map<String, dynamic>? _nextAppointment(List<Map<String, dynamic>> items) {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final upcoming = items.where((item) {
    final date = DateTime.tryParse('${item['fecha'] ?? ''}');
    return date != null && !date.isBefore(today);
  }).toList();
  if (upcoming.isEmpty) return null;
  upcoming.sort((a, b) {
    final byDate = '${a['fecha']}'.compareTo('${b['fecha']}');
    return byDate != 0 ? byDate : '${a['hora']}'.compareTo('${b['hora']}');
  });
  return upcoming.first;
}

Widget _nextAppointmentCard(
  BuildContext context,
  Map<String, dynamic>? appointment,
) {
  if (appointment == null) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            const _IconBox(icon: Icons.event_available_outlined),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Próxima cita médica',
                    style: Theme.of(context).textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 3),
                  const Text(
                    'No tienes citas próximas registradas.',
                    style: TextStyle(color: ClinicColors.muted, fontSize: 13),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
  final doctor = appointment['medico'] is Map
      ? Map<String, dynamic>.from(appointment['medico'] as Map)
      : <String, dynamic>{};
  return Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _Badge(
                icon: Icons.calendar_today_outlined,
                label: 'Próxima cita médica',
              ),
              _Badge(
                icon: Icons.check_circle_outline,
                label: _statusLabel(appointment['estado']),
              ),
            ],
          ),
          const SizedBox(height: 15),
          Row(
            children: [
              const CircleAvatar(
                backgroundColor: ClinicColors.soft,
                foregroundColor: ClinicColors.primary,
                child: Icon(Icons.person_outline),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      doctor['nombre']?.toString() ?? 'Médico',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    Text(
                      doctor['especialidad']?.toString() ?? '',
                      style: const TextStyle(
                        color: ClinicColors.muted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const Divider(height: 24),
          Row(
            children: [
              const Icon(
                Icons.schedule_outlined,
                size: 18,
                color: ClinicColors.muted,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${_dateLabel(appointment['fecha'])} · ${_timeLabel(appointment['hora'])}',
                  style: const TextStyle(fontSize: 13),
                ),
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class _ShortcutCard extends StatelessWidget {
  const _ShortcutCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    child: InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(13),
        child: Row(
          children: [
            _IconBox(icon: icon),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: ClinicColors.muted,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: ClinicColors.muted),
          ],
        ),
      ),
    ),
  );
}

class _IconBox extends StatelessWidget {
  const _IconBox({required this.icon});
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
    width: 42,
    height: 42,
    decoration: BoxDecoration(
      color: ClinicColors.soft,
      borderRadius: BorderRadius.circular(13),
    ),
    child: Icon(icon, color: ClinicColors.primary, size: 21),
  );
}

class _Badge extends StatelessWidget {
  const _Badge({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: ClinicColors.mint,
      borderRadius: BorderRadius.circular(20),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: ClinicColors.primary),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(
            color: ClinicColors.dark,
            fontSize: 10,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    ),
  );
}

String _statusLabel(dynamic status) => switch (status?.toString()) {
  'CONFIRMADA' => 'Confirmada',
  'PROGRAMADA' => 'Programada',
  'ATENDIDA' => 'Atendida',
  'CANCELADA' => 'Cancelada',
  'NO_ASISTIO' => 'No asistió',
  _ => 'Registrada',
};

String _dateLabel(dynamic value) {
  final date = DateTime.tryParse(value?.toString() ?? '');
  if (date == null) return value?.toString() ?? 'Fecha pendiente';
  return '${date.day}/${date.month}/${date.year}';
}

String _timeLabel(dynamic value) =>
    value?.toString().split(':').take(2).join(':') ?? 'Hora pendiente';
