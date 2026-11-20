import 'package:flutter/material.dart';

import '../../core/notifications/notification_inbox.dart';
import 'notification_inbox_sheet.dart';

class NotificationBell extends StatelessWidget {
  const NotificationBell({
    super.key,
    required this.inbox,
    required this.color,
    required this.badgeColor,
  });

  final NotificationInboxController inbox;
  final Color color;
  final Color badgeColor;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: inbox,
    builder: (context, _) => IconButton(
      tooltip: inbox.unreadCount == 0
          ? 'Notificaciones'
          : '${inbox.unreadCount} notificaciones sin leer',
      onPressed: () => _openInbox(context),
      icon: Stack(
        clipBehavior: Clip.none,
        children: [
          Icon(Icons.notifications_none_rounded, color: color),
          if (inbox.unreadCount > 0)
            Positioned(
              right: -7,
              top: -5,
              child: Container(
                constraints: const BoxConstraints(minWidth: 17, minHeight: 17),
                padding: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  color: badgeColor,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.white, width: 1.5),
                ),
                alignment: Alignment.center,
                child: Text(
                  inbox.unreadCount > 99 ? '99+' : '${inbox.unreadCount}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
        ],
      ),
    ),
  );

  Future<void> _openInbox(BuildContext context) async {
    await inbox.refresh();
    if (!context.mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => NotificationInboxSheet(inbox: inbox, accentColor: color),
    );
  }
}
