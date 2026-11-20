import 'dart:async';

import 'package:flutter/widgets.dart';

import '../network/api_client.dart';

class InboxNotification {
  const InboxNotification({
    required this.id,
    required this.title,
    required this.body,
    required this.createdAt,
    required this.isRead,
  });

  final int id;
  final String title;
  final String body;
  final DateTime? createdAt;
  final bool isRead;

  factory InboxNotification.fromJson(Map<String, dynamic> json) =>
      InboxNotification(
        id: (json['id'] as num).toInt(),
        title: json['titulo'] as String? ?? 'Notificación',
        body: json['cuerpo'] as String? ?? '',
        createdAt: DateTime.tryParse(json['creada_en']?.toString() ?? '')
            ?.toLocal(),
        isRead: json['leida'] == true,
      );

  InboxNotification copyWith({bool? isRead}) => InboxNotification(
    id: id,
    title: title,
    body: body,
    createdAt: createdAt,
    isRead: isRead ?? this.isRead,
  );
}

class NotificationInboxController extends ChangeNotifier
    with WidgetsBindingObserver {
  NotificationInboxController(this.api) {
    WidgetsBinding.instance.addObserver(this);
  }

  final ApiClient api;
  List<InboxNotification> notifications = const [];
  int unreadCount = 0;
  bool isLoading = false;
  bool _refreshing = false;
  bool _refreshAgain = false;
  int refreshVersion = 0;

  Future<void> refresh() async {
    if (_refreshing) {
      _refreshAgain = true;
      return;
    }
    _refreshing = true;
    isLoading = true;
    notifyListeners();
    try {
      do {
        _refreshAgain = false;
        try {
          final data = await api.getMap('notificaciones/');
          final rows = data['resultados'];
          notifications = rows is List
              ? rows
                    .whereType<Map>()
                    .map(
                      (row) => InboxNotification.fromJson(
                        row.map(
                          (key, value) => MapEntry(key.toString(), value),
                        ),
                      ),
                    )
                    .toList()
              : const [];
          unreadCount = (data['no_leidas'] as num?)?.toInt() ?? 0;
          refreshVersion++;
        } catch (_) {
          // Keep the most recent inbox available if the network is temporarily down.
        }
      } while (_refreshAgain);
    } finally {
      isLoading = false;
      _refreshing = false;
      notifyListeners();
    }
  }

  Future<void> markRead(int id) async {
    try {
      await api.postMap('notificaciones/$id/leer/');
      await refresh();
    } catch (_) {
      await refresh();
    }
  }

  Future<void> markAllRead() async {
    try {
      await api.postMap('notificaciones/', data: const {});
      notifications = notifications
          .map((item) => item.copyWith(isRead: true))
          .toList();
      unreadCount = 0;
      notifyListeners();
    } catch (_) {
      await refresh();
    }
  }

  void clear() {
    notifications = const [];
    unreadCount = 0;
    notifyListeners();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) unawaited(refresh());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
