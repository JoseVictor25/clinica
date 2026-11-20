import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/notifications/notification_inbox.dart';

class NotificationInboxSheet extends StatelessWidget {
  const NotificationInboxSheet({
    super.key,
    required this.inbox,
    required this.accentColor,
  });

  final NotificationInboxController inbox;
  final Color accentColor;

  @override
  Widget build(BuildContext context) => SafeArea(
    top: false,
    child: Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.sizeOf(context).height * .78,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(height: 10),
          Container(
            width: 38,
            height: 4,
            decoration: BoxDecoration(
              color: const Color(0xFFD5DEDA),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 15, 12, 10),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    'Notificaciones${inbox.unreadCount > 0 ? ' (${inbox.unreadCount})' : ''}',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                if (inbox.unreadCount > 0)
                  TextButton(
                    onPressed: inbox.markAllRead,
                    child: const Text('Marcar leídas'),
                  ),
              ],
            ),
          ),
          const Divider(height: 1),
          Flexible(
            child: AnimatedBuilder(
              animation: inbox,
              builder: (context, _) {
                if (inbox.isLoading && inbox.notifications.isEmpty) {
                  return const Center(
                    child: Padding(
                      padding: EdgeInsets.all(28),
                      child: CircularProgressIndicator(),
                    ),
                  );
                }
                if (inbox.notifications.isEmpty) {
                  return const Center(
                    child: Padding(
                      padding: EdgeInsets.all(28),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.notifications_none,
                            size: 38,
                            color: Color(0xFF82918C),
                          ),
                          SizedBox(height: 8),
                          Text('No tienes notificaciones todavía.'),
                        ],
                      ),
                    ),
                  );
                }
                return ListView.separated(
                  shrinkWrap: true,
                  padding: const EdgeInsets.fromLTRB(14, 8, 14, 18),
                  itemCount: inbox.notifications.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 7),
                  itemBuilder: (context, index) {
                    final notification = inbox.notifications[index];
                    return Material(
                      color: notification.isRead
                          ? Colors.white
                          : accentColor.withValues(alpha: .07),
                      borderRadius: BorderRadius.circular(14),
                      child: ListTile(
                        onTap: notification.isRead
                            ? null
                            : () => inbox.markRead(notification.id),
                        leading: Icon(
                          notification.isRead
                              ? Icons.notifications_none
                              : Icons.notifications_active_outlined,
                          color: accentColor,
                        ),
                        title: Text(
                          notification.title,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(notification.body),
                            if (notification.createdAt != null) ...[
                              const SizedBox(height: 4),
                              Text(
                                DateFormat('dd/MM/yyyy · HH:mm')
                                    .format(notification.createdAt!),
                                style: const TextStyle(fontSize: 11),
                              ),
                            ],
                          ],
                        ),
                        trailing: notification.isRead
                            ? null
                            : Container(
                                width: 8,
                                height: 8,
                                decoration: BoxDecoration(
                                  color: accentColor,
                                  shape: BoxShape.circle,
                                ),
                              ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    ),
  );
}
