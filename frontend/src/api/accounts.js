import apiClient from './client';

export const accountsApi = {
  // College profile (Representative)
  async getCollegeMe() {
    const res = await apiClient.get('/colleges/me');
    return res.data;
  },

  async updateCollegeMe(data) {
    const res = await apiClient.patch('/colleges/me', data);
    return res.data;
  },

  // College management (Platform Admin)
  async listColleges(page = 1, pageSize = 20) {
    const res = await apiClient.get('/colleges', {
      params: { page, page_size: pageSize },
    });
    return res.data;
  },

  async getCollege(collegeId) {
    const res = await apiClient.get(`/colleges/${collegeId}`);
    return res.data;
  },

  async verifyCollege(collegeId, verificationStatus) {
    const res = await apiClient.patch(`/admin/colleges/${collegeId}/verification`, {
      verification_status: verificationStatus,
    });
    return res.data;
  },

  // User profile
  async getUserMe() {
    const res = await apiClient.get('/users/me');
    return res.data;
  },

  async updateUserMe(data) {
    const res = await apiClient.patch('/users/me', data);
    return res.data;
  },

  // College Team (Representative)
  async listCollegeUsers(page = 1, pageSize = 20) {
    const res = await apiClient.get('/colleges/me/users', {
      params: { page, page_size: pageSize },
    });
    return res.data;
  },

  async createCollegeUser(data) {
    const res = await apiClient.post('/colleges/me/users', data);
    return res.data;
  },

  // User status toggle (Representative / Admin)
  async updateUserStatus(userId, isActive) {
    const res = await apiClient.patch(`/users/${userId}/status`, {
      is_active: isActive,
    });
    return res.data;
  },
};

export default accountsApi;
