import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/models/page_result.dart';
import '../../../core/notifications/notification_inbox.dart';
import '../data/doctor_api.dart';
import '../doctor_theme.dart';

class DoctorDashboardScreen extends StatefulWidget {
  const DoctorDashboardScreen({
    super.key,
    required this.api,
    required this.inbox,
    required this.username,
    required this.onOpenAgenda,
    required this.onOpenPatients,
  });

  final DoctorApi api;
  final NotificationInboxController inbox;
  final String username;
  final VoidCallback onOpenAgenda;
  final VoidCallback onOpenPatients;

  @override
  State<DoctorDashboardScreen> createState() => _DoctorDashboardScreenState();
}

class _DashboardData {
  const _DashboardData(this.doctor, this.appointments, this.patients);

  final Map<String, dynamic>? doctor;
  final PageResult appointments;
  final PageResult patients;
}

class _DoctorDashboardScreenState extends State<DoctorDashboardScreen> {
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
    final now = DateTime.now();
    final values = await Future.wait<Object?>([
      widget.api.doctorProfile(),
      widget.api.agenda(date: DateFormat('yyyy-MM-dd').format(now)),
      widget.api.patients(),
    ]);
    return _DashboardData(
      values[0] as Map<String, dynamic>?,
      values[1] as PageResult,
      values[2] as PageResult,
    );
  }

  void _reload() {
    final future = _load();
    setState(() => _future = future);
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<_DashboardData>(
    future: _future,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return _ErrorState(error: snapshot.error!, onRetry: _reload);
      }
      final data = snapshot.data!;
      final profile = data.doctor;
      final displayName = profile?['personal_nombre']?.toString().trim();
      final name = displayName?.isNotEmpty == true
          ? displayName!
          : widget.username;
      final next = _nextAppointment(data.appointments.results);
      final appointmentsToday = data.appointments.count;
      final pending = data.appointments.results
          .where((item) => _isPending(item['estado']))
          .length;

      return RefreshIndicator(
        onRefresh: () async {
          final future = _load();
          setState(() => _future = future);
          try {
            await future;
          } catch (_) {
            // El estado de error permanece visible con la opción de reintento.
          }
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(17, 10, 17, 24),
          children: [
            Text(
              'Hola, Dr. $name',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: DoctorColors.text,
                fontWeight: FontWeight.w800,
                letterSpacing: -.5,
              ),
            ),
            const SizedBox(height: 5),
            Text(
              profile?['especialidad_nombre']?.toString() ?? 'Panel médico',
              style: const TextStyle(color: DoctorColors.muted, fontSize: 13),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: _MetricCard(
                    label: 'Citas hoy',
                    value: '$appointmentsToday',
                    icon: Icons.calendar_today_outlined,
                  ),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: _MetricCard(
                    label: 'Pacientes',
                    value: '${data.patients.count}',
                    icon: Icons.people_alt_outlined,
                    onTap: widget.onOpenPatients,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 17),
            _NextAppointmentCard(
              appointment: next,
              onOpenAgenda: widget.onOpenAgenda,
            ),
            const SizedBox(height: 21),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Citas de hoy',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: DoctorColors.text,
                  ),
                ),
                TextButton(
                  onPressed: widget.onOpenAgenda,
                  child: const Text('Ver agenda'),
                ),
              ],
            ),
            if (data.appointments.results.isEmpty)
              const _InfoCard(
                icon: Icons.event_available_outlined,
                text: 'No tienes citas programadas para hoy.',
              )
            else
              ...data.appointments.results
                  .take(4)
                  .map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: 9),
                      child: _TodayAppointmentCard(item: item),
                    ),
                  ),
            const SizedBox(height: 12),
            _QuickAccessCard(
              title: 'Gestión de pacientes',
              detail: 'Busca pacientes y consulta su historia clínica.',
              icon: Icons.medical_information_outlined,
              onTap: widget.onOpenPatients,
            ),
            if (pending > 0) ...[
              const SizedBox(height: 10),
              Text(
                '$pending cita${pending == 1 ? '' : 's'} pendiente${pending == 1 ? '' : 's'} de atención',
                style: const TextStyle(color: DoctorColors.muted, fontSize: 12),
              ),
            ],
          ],
        ),
      );
    },
  );
}

Map<String, dynamic>? _nextAppointment(List<Map<String, dynamic>> items) {
  final eligible = items.where((item) => _isPending(item['estado'])).toList();
  eligible.sort((a, b) => '${a['hora']}'.compareTo('${b['hora']}'));
  return eligible.isEmpty ? null : eligible.first;
}

bool _isPending(dynamic status) =>
    status == 'PROGRAMADA' || status == 'CONFIRMADA';

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
    this.onTap,
  });

  final String label;
  final String value;
  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Card(
    clipBehavior: Clip.antiAlias,
    child: InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(9),
            decoration: BoxDecoration(
              color: DoctorColors.soft,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, size: 19, color: DoctorColors.teal),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    color: DoctorColors.muted,
                    fontSize: 11,
                  ),
                ),
                Text(
                  value,
                  style: const TextStyle(
                    color: DoctorColors.text,
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      ),
    ),
  );
}

class _NextAppointmentCard extends StatelessWidget {
  const _NextAppointmentCard({
    required this.appointment,
    required this.onOpenAgenda,
  });
  final Map<String, dynamic>? appointment;
  final VoidCallback onOpenAgenda;

  @override
  Widget build(BuildContext context) {
    final item = appointment;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: item == null
            ? const _InfoCard(
                icon: Icons.event_note_outlined,
                text: 'No hay próximas citas para atender.',
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'PRÓXIMA CONSULTA',
                        style: TextStyle(
                          color: DoctorColors.teal,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          letterSpacing: .5,
                        ),
                      ),
                      Text(
                        _time(item['hora']),
                        style: const TextStyle(
                          color: DoctorColors.teal,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      const CircleAvatar(
                        backgroundColor: DoctorColors.soft,
                        foregroundColor: DoctorColors.teal,
                        child: Icon(Icons.person_outline),
                      ),
                      const SizedBox(width: 11),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item['paciente_nombre']?.toString() ?? 'Paciente',
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            Text(
                              item['especialidad_nombre']?.toString() ??
                                  'Cita médica',
                              style: const TextStyle(
                                color: DoctorColors.muted,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                      FilledButton(
                        onPressed: onOpenAgenda,
                        child: const Text('Ver'),
                      ),
                    ],
                  ),
                ],
              ),
      ),
    );
  }
}

class _TodayAppointmentCard extends StatelessWidget {
  const _TodayAppointmentCard({required this.item});
  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final attended = item['estado'] == 'ATENDIDA';
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 12),
        child: Row(
          children: [
            Container(
              width: 47,
              height: 47,
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
                    'hoy',
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
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  Text(
                    item['especialidad_nombre']?.toString() ??
                        item['motivo']?.toString() ??
                        'Consulta',
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
            _StatusBadge(
              label:
                  item['estado_display']?.toString() ??
                  item['estado']?.toString() ??
                  'Registrada',
              attended: attended,
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.attended});
  final String label;
  final bool attended;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: attended ? DoctorColors.lavender : DoctorColors.soft,
      borderRadius: BorderRadius.circular(14),
    ),
    child: Text(
      label,
      style: const TextStyle(
        fontSize: 10,
        color: DoctorColors.darkTeal,
        fontWeight: FontWeight.w700,
      ),
    ),
  );
}

class _QuickAccessCard extends StatelessWidget {
  const _QuickAccessCard({
    required this.title,
    required this.detail,
    required this.icon,
    required this.onTap,
  });
  final String title;
  final String detail;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      onTap: onTap,
      leading: CircleAvatar(
        backgroundColor: DoctorColors.soft,
        foregroundColor: DoctorColors.teal,
        child: Icon(icon),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text(detail, maxLines: 1, overflow: TextOverflow.ellipsis),
      trailing: const Icon(Icons.chevron_right_rounded),
    ),
  );
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Icon(icon, color: DoctorColors.teal, size: 20),
      const SizedBox(width: 9),
      Expanded(
        child: Text(
          text,
          style: const TextStyle(color: DoctorColors.muted, fontSize: 13),
        ),
      ),
    ],
  );
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
          Text(error.toString(), textAlign: TextAlign.center),
          const SizedBox(height: 10),
          OutlinedButton(onPressed: onRetry, child: const Text('Reintentar')),
        ],
      ),
    ),
  );
}

String _time(dynamic value) =>
    value?.toString().split(':').take(2).join(':') ?? '--:--';
