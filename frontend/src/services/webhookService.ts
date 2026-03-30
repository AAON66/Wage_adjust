import api from './api';
import type { WebhookEndpointRead, WebhookEndpointCreatePayload, WebhookDeliveryLogRead } from '../types/api';

export async function registerWebhook(payload: WebhookEndpointCreatePayload): Promise<WebhookEndpointRead> {
  const { data } = await api.post<WebhookEndpointRead>('/webhooks/', payload);
  return data;
}

export async function listWebhooks(): Promise<WebhookEndpointRead[]> {
  const { data } = await api.get<WebhookEndpointRead[]>('/webhooks/');
  return data;
}

export async function unregisterWebhook(webhookId: string): Promise<void> {
  await api.delete(`/webhooks/${webhookId}`);
}

export async function getWebhookLogs(webhookId: string, limit = 50): Promise<WebhookDeliveryLogRead[]> {
  const { data } = await api.get<WebhookDeliveryLogRead[]>(`/webhooks/${webhookId}/logs`, { params: { limit } });
  return data;
}
