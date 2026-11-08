import apiClient from './client';

export const resourcesApi = {
  async listResources(params = {}) {
    const res = await apiClient.get('/resources', { params });
    return res.data;
  },

  async getResource(resourceId) {
    const res = await apiClient.get(`/resources/${resourceId}`);
    return res.data;
  },

  async createResource(data) {
    const res = await apiClient.post('/resources', data);
    return res.data;
  },

  async updateResource(resourceId, data) {
    const res = await apiClient.patch(`/resources/${resourceId}`, data);
    return res.data;
  },

  async updateResourceStatus(resourceId, status) {
    const res = await apiClient.patch(`/resources/${resourceId}/status`, { status });
    return res.data;
  },

  async getMyInventory() {
    const res = await apiClient.get('/inventory/me');
    return res.data;
  },

  async uploadImage(resourceId, file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post(`/resources/${resourceId}/image`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  getImageUrl(resourceId) {
    const base = apiClient.defaults.baseURL || '/api/v1';
    return `${base}/resources/${resourceId}/image`;
  },

  async deleteImage(resourceId) {
    const res = await apiClient.delete(`/resources/${resourceId}/image`);
    return res.data;
  },
};

export default resourcesApi;
