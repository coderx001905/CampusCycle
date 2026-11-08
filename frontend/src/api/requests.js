import apiClient from './client';

export const requestsApi = {
  async submitRequest(data) {
    const res = await apiClient.post('/requests', data);
    return res.data;
  },

  async getMine(page = 1, pageSize = 20) {
    const res = await apiClient.get('/requests/mine', {
      params: { page, page_size: pageSize },
    });
    return res.data;
  },

  async getReceived(page = 1, pageSize = 20) {
    const res = await apiClient.get('/requests/received', {
      params: { page, page_size: pageSize },
    });
    return res.data;
  },

  async getRequest(requestId) {
    const res = await apiClient.get(`/requests/${requestId}`);
    return res.data;
  },

  async approveRequest(requestId, approvedQuantity = null) {
    const payload = approvedQuantity ? { approved_quantity: approvedQuantity } : null;
    const res = await apiClient.post(`/requests/${requestId}/approve`, payload);
    return res.data;
  },

  async rejectRequest(requestId, reason) {
    const res = await apiClient.post(`/requests/${requestId}/reject`, { reason });
    return res.data;
  },

  async confirmPurchase(requestId) {
    const res = await apiClient.post(`/requests/${requestId}/purchase-confirmation`);
    return res.data;
  },

  async cancelRequest(requestId, reason) {
    const res = await apiClient.post(`/requests/${requestId}/cancel`, { reason });
    return res.data;
  },

  async decideCancellation(requestId, decision) {
    const res = await apiClient.post(`/requests/${requestId}/cancellation-decision`, { decision });
    return res.data;
  },
};

export default requestsApi;
