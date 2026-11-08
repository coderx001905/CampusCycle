import apiClient from './client';

export const transfersApi = {
  async createTransfer(requestId, data) {
    const res = await apiClient.post(`/requests/${requestId}/transfers`, data);
    return res.data;
  },

  async listTransfers(params = {}) {
    const res = await apiClient.get('/transfers', { params });
    return res.data;
  },

  async getTransfer(transferId) {
    const res = await apiClient.get(`/transfers/${transferId}`);
    return res.data;
  },

  async getTransferHistory(transferId) {
    const res = await apiClient.get(`/transfers/${transferId}/history`);
    return res.data;
  },

  async dispatchTransfer(transferId, data = {}) {
    const res = await apiClient.post(`/transfers/${transferId}/dispatch`, data);
    return res.data;
  },

  async confirmReceipt(transferId, data) {
    const res = await apiClient.post(`/transfers/${transferId}/receipt`, data);
    return res.data;
  },

  async cancelTransfer(transferId, reason) {
    const res = await apiClient.post(`/transfers/${transferId}/cancel`, { reason });
    return res.data;
  },

  async decideCancellation(transferId, decision) {
    const res = await apiClient.post(`/transfers/${transferId}/cancellation-decision`, { decision });
    return res.data;
  },

  async resolveDispute(transferId, data) {
    const res = await apiClient.post(`/transfers/${transferId}/dispute-resolution`, data);
    return res.data;
  },
};

export default transfersApi;
