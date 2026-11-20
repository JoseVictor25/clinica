import 'package:flutter/material.dart';

import '../../../core/models/page_result.dart';
import '../../../core/notifications/notification_inbox.dart';
import '../clinic_theme.dart';
import '../data/patient_api.dart';
import '../widgets/patient_portal_error.dart';
import '../../shared/telemedicine_call_screen.dart';

class PatientAppointmentsScreen extends StatefulWidget {
  const PatientAppointmentsScreen({
    super.key,
    required this.api,
    required this.inbox,
  });
  final PatientApi api;
  final NotificationInboxController inbox;

  @override
  State<PatientAppointmentsScreen> createState() =>
      _PatientAppointmentsScreenState();
}

class _PatientAppointmentsScreenState extends State<PatientAppointmentsScreen> {
  int _page = 1;
  String _state = '';
  late Future<PageResult> _future;
  late int _lastInboxRefresh;
  @override
  void initState() {
    super.initState();
    _lastInboxRefresh = widget.inbox.refreshVersion;
    widget.inbox.addListener(_onInboxChanged);
    _reload();
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

  void _reload() {
    final future = widget.api.appointments(page: _page, state: _state);
    setState(() {
      _future = future;
    });
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Mis citas',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w800,
                color: ClinicColors.text,
              ),
            ),
            const SizedBox(height: 3),
            const Text(
              'Consulta tus próximas citas y su estado.',
              style: TextStyle(color: ClinicColors.muted, fontSize: 13),
            ),
            const SizedBox(height: 13),
            DropdownButtonFormField<String>(
              initialValue: _state,
              decoration: const InputDecoration(
                labelText: 'Filtrar por estado',
                prefixIcon: Icon(Icons.filter_list),
                isDense: true,
              ),
              items: const [
                DropdownMenuItem(value: '', child: Text('Todos los estados')),
                DropdownMenuItem(
                  value: 'PROGRAMADA',
                  child: Text('Programada'),
                ),
                DropdownMenuItem(
                  value: 'CONFIRMADA',
                  child: Text('Confirmada'),
                ),
                DropdownMenuItem(value: 'ATENDIDA', child: Text('Atendida')),
                DropdownMenuItem(value: 'CANCELADA', child: Text('Cancelada')),
                DropdownMenuItem(
                  value: 'NO_ASISTIO',
                  child: Text('No asistió'),
                ),
              ],
              onChanged: (value) {
                setState(() {
                  _state = value ?? '';
                  _page = 1;
                });
                _reload();
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
              return PatientPortalError(
                error: snapshot.error!,
                onRetry: _reload,
              );
            }
            final page = snapshot.data!;
            if (page.results.isEmpty) {
              return const Center(
                child: Text('No hay citas para este filtro.'),
              );
            }
            return RefreshIndicator(
              onRefresh: () async => _reload(),
              child: ListView.builder(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 20),
                itemCount: page.results.length + 1,
                itemBuilder: (context, index) {
                  if (index == page.results.length) {
                    final maxPage = (page.count / 10).ceil();
                    return Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        IconButton(
                          onPressed: _page > 1
                              ? () {
                                  setState(() {
                                    _page--;
                                  });
                                  _reload();
                                }
                              : null,
                          icon: const Icon(Icons.chevron_left),
                        ),
                        Text(
                          'Página $_page${maxPage > 0 ? ' de $maxPage' : ''}',
                        ),
                        IconButton(
                          onPressed: _page * 10 < page.count
                              ? () {
                                  setState(() {
                                    _page++;
                                  });
                                  _reload();
                                }
                              : null,
                          icon: const Icon(Icons.chevron_right),
                        ),
                      ],
                    );
                  }
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _appointmentCard(context, page.results[index]),
                  );
                },
              ),
            );
          },
        ),
      ),
    ],
  );
}

Widget _appointmentCard(BuildContext context, Map<String, dynamic> item) {
  final physician = item['medico'] is Map
      ? Map<String, dynamic>.from(item['medico'] as Map)
      : <String, dynamic>{};
  final status = (item['estado'] ?? '').toString();
  return Card(
    child: InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: () => showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (_) => _appointmentDetails(context, item, physician),
      ),
      child: Padding(
        padding: const EdgeInsets.all(17),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: ClinicColors.soft,
                    borderRadius: BorderRadius.circular(13),
                  ),
                  child: const Icon(
                    Icons.medical_services_outlined,
                    color: ClinicColors.primary,
                  ),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${item['fecha'] ?? ''} · ${(item['hora'] ?? '').toString().split(':').take(2).join(':')}',
                        style: Theme.of(context).textTheme.titleSmall
                            ?.copyWith(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        physician['especialidad']?.toString() ??
                            'Consulta médica',
                        style: const TextStyle(
                          color: ClinicColors.muted,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                _appointmentStatus(status),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              physician['nombre']?.toString() ?? 'Médico por confirmar',
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              item['motivo']?.toString().isNotEmpty == true
                  ? item['motivo'].toString()
                  : 'Sin motivo especificado',
              style: const TextStyle(color: ClinicColors.muted, fontSize: 12),
            ),
            const SizedBox(height: 8),
            Text(
              item['modalidad_display']?.toString() ??
                  item['modalidad']?.toString() ??
                  '',
              style: const TextStyle(color: ClinicColors.primary, fontSize: 12),
            ),
          ],
        ),
      ),
    ),
  );
}

Widget _appointmentDetails(
  BuildContext context,
  Map<String, dynamic> item,
  Map<String, dynamic> physician,
) => SafeArea(
  child: Padding(
    padding: const EdgeInsets.all(20),
    child: Wrap(
      runSpacing: 12,
      children: [
        Text(
          'Detalle de la cita',
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
        ),
        _detail('Fecha', item['fecha']),
        _detail('Hora', item['hora']),
        _detail('Estado', item['estado']),
        _detail('Modalidad', item['modalidad_display'] ?? item['modalidad']),
        _detail(
          'Médico',
          '${physician['nombre'] ?? '—'} · ${physician['especialidad'] ?? ''}',
        ),
        _detail('Motivo', item['motivo']),
        if (item['link_videollamada'] is String &&
            (item['link_videollamada'] as String).isNotEmpty)
          FilledButton.icon(
            onPressed: statusAllowsRoom(item['estado'])
                ? () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => TelemedicineCallScreen(
                        roomUrl: item['link_videollamada'] as String,
                        displayName: 'Paciente',
                        otherParticipantName:
                            physician['nombre']?.toString() ?? 'Médico',
                      ),
                    ),
                  )
                : null,
            icon: const Icon(Icons.video_call_outlined),
            label: const Text('Ingresar a sala virtual'),
          ),
      ],
    ),
  ),
);

Widget _detail(String label, dynamic value) =>
    SizedBox(width: double.infinity, child: Text('$label: ${value ?? '—'}'));

Widget _appointmentStatus(String status) {
  final label = switch (status) {
    'CONFIRMADA' => 'Confirmada',
    'PROGRAMADA' => 'Programada',
    'ATENDIDA' => 'Atendida',
    'CANCELADA' => 'Cancelada',
    'NO_ASISTIO' => 'No asistió',
    _ => status,
  };
  final color = switch (status) {
    'CONFIRMADA' || 'ATENDIDA' => ClinicColors.primary,
    'CANCELADA' || 'NO_ASISTIO' => const Color(0xFFB42318),
    _ => const Color(0xFF9A6700),
  };
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(18),
    ),
    child: Text(
      label,
      style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: color),
    ),
  );
}

bool statusAllowsRoom(dynamic value) =>
    value != 'CANCELADA' && value != 'NO_ASISTIO';
