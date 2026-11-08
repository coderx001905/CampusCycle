import React, { useEffect, useState, useCallback } from 'react';
import { Building2, Users, Save, Plus, ShieldAlert, CheckCircle2, UserCheck, UserX, Loader2 } from 'lucide-react';
import { accountsApi } from '../../api/accounts';
import { useAuth } from '../../context/AuthContext';

export const CollegeSettingsView = ({ onShowToast }) => {
  const { user, isCollegeRep } = useAuth();
  const [college, setCollege] = useState(null);
  const [team, setTeam] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingCollege, setIsSavingCollege] = useState(false);
  const [isAddingUser, setIsAddingUser] = useState(false);

  // College form state
  const [collegeForm, setCollegeForm] = useState({
    name: '',
    city: '',
    address: '',
    contact_email: '',
  });

  // New user form state
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUserForm, setNewUserForm] = useState({
    name: '',
    email: '',
    password: '',
  });

  const fetchData = useCallback(async () => {
    if (!isCollegeRep) return;
    setIsLoading(true);
    try {
      const [colRes, teamRes] = await Promise.all([
        accountsApi.getCollegeMe(),
        accountsApi.listCollegeUsers(1, 50),
      ]);

      if (colRes?.data) {
        setCollege(colRes.data);
        setCollegeForm({
          name: colRes.data.name || '',
          city: colRes.data.city || '',
          address: colRes.data.address || '',
          contact_email: colRes.data.contact_email || '',
        });
      }

      if (teamRes?.data?.items) {
        setTeam(teamRes.data.items);
      }
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Error',
        message: err.message || 'Failed to load college settings.',
      });
    } finally {
      setIsLoading(false);
    }
  }, [isCollegeRep, onShowToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleUpdateCollege = async (e) => {
    e.preventDefault();
    setIsSavingCollege(true);
    try {
      const res = await accountsApi.updateCollegeMe(collegeForm);
      setCollege(res.data);
      onShowToast?.({
        type: 'success',
        title: 'College Profile Updated',
        message: 'Institution profile details have been saved successfully.',
      });
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Update Failed',
        message: err.response?.data?.detail || err.message || 'Could not update college profile.',
      });
    } finally {
      setIsSavingCollege(false);
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    if (newUserForm.password.length < 12) {
      onShowToast?.({
        type: 'error',
        title: 'Validation Error',
        message: 'Password must be at least 12 characters long.',
      });
      return;
    }

    setIsAddingUser(true);
    try {
      await accountsApi.createCollegeUser(newUserForm);
      onShowToast?.({
        type: 'success',
        title: 'Representative Added',
        message: `Account for ${newUserForm.name} created successfully.`,
      });
      setShowAddUserModal(false);
      setNewUserForm({ name: '', email: '', password: '' });
      await fetchData();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Creation Failed',
        message: err.response?.data?.detail || err.message || 'Failed to create representative account.',
      });
    } finally {
      setIsAddingUser(false);
    }
  };

  const handleToggleUserStatus = async (targetUser) => {
    const newStatus = !targetUser.is_active;
    try {
      await accountsApi.updateUserStatus(targetUser.id, newStatus);
      onShowToast?.({
        type: 'success',
        title: 'Status Updated',
        message: `Account has been ${newStatus ? 'activated' : 'deactivated'}.`,
      });
      await fetchData();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Action Blocked',
        message:
          err.response?.data?.detail ||
          err.response?.data?.error?.message ||
          'Could not modify user status.',
      });
    }
  };

  if (!isCollegeRep) {
    return (
      <div className="p-8 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
        <ShieldAlert className="w-10 h-10 text-amber-500 mx-auto mb-2" />
        <h3 className="text-base font-bold text-slate-800 dark:text-white">Settings Restricted</h3>
        <p className="text-xs text-slate-500 mt-1">College settings are only accessible to designated college representatives.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin mr-3 text-blue-600" />
        <span className="text-sm font-medium">Loading institution profile & team...</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-8 animate-in fade-in duration-200">
      <div>
        <h1 className="text-2xl font-bold font-display text-slate-900 dark:text-white flex items-center gap-2.5">
          <Building2 className="w-7 h-7 text-blue-600 dark:text-blue-400" />
          College Profile & Team Management
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Manage your institution's public profile, address, and representative team accounts.
        </p>
      </div>

      {/* College Info Form */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100 dark:border-slate-700">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Institution Profile</h2>
            <p className="text-xs text-slate-500">Public profile details displayed across the resource marketplace.</p>
          </div>
          <span className="px-3 py-1 text-xs font-bold rounded-full capitalize bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300">
            {college?.verification_status || 'Verified'}
          </span>
        </div>

        <form onSubmit={handleUpdateCollege} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Institution Name *
              </label>
              <input
                type="text"
                required
                value={collegeForm.name}
                onChange={(e) => setCollegeForm({ ...collegeForm, name: e.target.value })}
                className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                City *
              </label>
              <input
                type="text"
                required
                value={collegeForm.city}
                onChange={(e) => setCollegeForm({ ...collegeForm, city: e.target.value })}
                className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Contact Email *
            </label>
            <input
              type="email"
              required
              value={collegeForm.contact_email}
              onChange={(e) => setCollegeForm({ ...collegeForm, contact_email: e.target.value })}
              className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Campus Street Address *
            </label>
            <textarea
              rows="2"
              required
              value={collegeForm.address}
              onChange={(e) => setCollegeForm({ ...collegeForm, address: e.target.value })}
              className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-white"
            />
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isSavingCollege}
              className="py-2.5 px-5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-md flex items-center gap-2 disabled:opacity-50"
            >
              {isSavingCollege ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              <span>Save Changes</span>
            </button>
          </div>
        </form>
      </div>

      {/* Team Management */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100 dark:border-slate-700">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-blue-600" />
              Representative Team
            </h2>
            <p className="text-xs text-slate-500">Authorized personnel who can transact on behalf of your college.</p>
          </div>
          <button
            onClick={() => setShowAddUserModal(true)}
            className="py-2 px-3.5 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 text-blue-600 dark:text-blue-400 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add Representative</span>
          </button>
        </div>

        <div className="divide-y divide-slate-100 dark:divide-slate-700">
          {team.map((member) => {
            const isSelf = member.id === user?.id;

            return (
              <div key={member.id} className="py-3.5 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-700 dark:text-slate-200">
                    {member.name.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                      {member.name}
                      {isSelf && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 font-bold">
                          You
                        </span>
                      )}
                    </h4>
                    <p className="text-xs text-slate-500">{member.email}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`text-[11px] font-bold px-2.5 py-1 rounded-full capitalize ${
                      member.is_active
                        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                        : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
                    }`}
                  >
                    {member.is_active ? 'Active' : 'Inactive'}
                  </span>

                  <button
                    onClick={() => handleToggleUserStatus(member)}
                    disabled={isSelf && member.is_active}
                    title={isSelf ? 'Cannot deactivate your own active session' : 'Toggle status'}
                    className={`p-2 rounded-lg text-xs font-semibold transition-colors ${
                      member.is_active
                        ? 'text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20'
                        : 'text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20'
                    } disabled:opacity-30 disabled:cursor-not-allowed`}
                  >
                    {member.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md p-6 bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">
              Add College Representative
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Authorize a new representative account for {college?.name}.
            </p>

            <form onSubmit={handleAddUser} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={newUserForm.name}
                  onChange={(e) => setNewUserForm({ ...newUserForm, name: e.target.value })}
                  placeholder="e.g. Dr. Robert Chen"
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Email Address *
                </label>
                <input
                  type="email"
                  required
                  value={newUserForm.email}
                  onChange={(e) => setNewUserForm({ ...newUserForm, email: e.target.value })}
                  placeholder="r.chen@college.edu"
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Password (min 12 chars) *
                </label>
                <input
                  type="password"
                  required
                  minLength={12}
                  value={newUserForm.password}
                  onChange={(e) => setNewUserForm({ ...newUserForm, password: e.target.value })}
                  placeholder="••••••••••••"
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddUserModal(false)}
                  className="flex-1 py-2 px-4 border border-slate-300 dark:border-slate-600 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAddingUser}
                  className="flex-1 py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-md flex items-center justify-center gap-1.5 disabled:opacity-50"
                >
                  {isAddingUser ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  <span>Create Account</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default CollegeSettingsView;
