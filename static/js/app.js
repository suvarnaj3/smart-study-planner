/**
 * static/js/app.js
 * Smart Study Planner - Vanilla JS ES6 Dashboard Application.
 * Communicates with Flask REST API via Fetch API.
 */

const app = {
    state: {
        subjects: [],
        topics: [],
        exams: [],
        sessions: [],
        activeView: 'dashboard',
        lastScheduleResult: null
    },

    /**
     * Initializes application state and event listeners.
     */
    init: function () {
        this.setupNavigation();
        this.setDefaultTargetDate();
        this.refreshAllData();
    },

    /**
     * Generic API wrapper over Fetch API.
     */
    apiFetch: async function (url, method = 'GET', body = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, options);
            const data = await response.json();

            if (!response.ok) {
                const errorMsg = data.error || `HTTP ${response.status} ${response.statusText}`;
                throw new Error(errorMsg);
            }

            return data;
        } catch (error) {
            this.showToast(error.message, 'error');
            throw error;
        }
    },

    /**
     * Sets default target date input to today's YYYY-MM-DD.
     */
    setDefaultTargetDate: function () {
        const dateInput = document.getElementById('sched-date');
        if (dateInput) {
            const today = new Date().toISOString().split('T')[0];
            dateInput.value = today;
        }
    },

    /**
     * Navigation setup for switching dashboard views.
     */
    setupNavigation: function () {
        const navButtons = document.querySelectorAll('.nav-item');
        navButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const viewName = btn.getAttribute('data-view');
                this.switchView(viewName);
            });
        });
    },

    switchView: function (viewName) {
        this.state.activeView = viewName;

        // Update nav items active class
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-view') === viewName);
        });

        // Update view section active class
        document.querySelectorAll('.view-section').forEach(sec => {
            sec.classList.toggle('active', sec.id === `view-${viewName}`);
        });

        // Update Header titles
        const titleEl = document.getElementById('page-title');
        const subtitleEl = document.getElementById('page-subtitle');

        const titles = {
            dashboard: { title: "Dashboard Overview", subtitle: "Track overall study progress and generated sessions." },
            subjects: { title: "Subjects & Topics", subtitle: "Manage courses, estimated study hours, and prerequisites." },
            schedule: { title: "Study Schedule Generator", subtitle: "Greedy slot allocation powered by Binary Max-Heap." },
            prerequisites: { title: "Prerequisite Graph", subtitle: "Kahn's Topological Sort order and dependency locks." },
            progress: { title: "Progress Tracking", subtitle: "Update remaining study hours and mark topics complete." },
            exams: { title: "Upcoming Exams", subtitle: "Monitor upcoming exams and urgent subject deadlines." }
        };

        if (titles[viewName]) {
            titleEl.textContent = titles[viewName].title;
            subtitleEl.textContent = titles[viewName].subtitle;
        }

        // Render target view
        this.renderCurrentView();
    },

    /**
     * Re-fetches all state from Flask REST API.
     */
    refreshAllData: async function () {
        try {
            const [subjects, topics, exams, sessions] = await Promise.all([
                this.apiFetch('/api/subjects'),
                this.apiFetch('/api/topics'),
                this.apiFetch('/api/exams'),
                this.apiFetch('/api/sessions')
            ]);

            this.state.subjects = subjects;
            this.state.topics = topics;
            this.state.exams = exams;
            this.state.sessions = sessions;

            this.populateModalSelects();
            this.renderCurrentView();
        } catch (err) {
            console.error("Failed to load initial data:", err);
        }
    },

    renderCurrentView: function () {
        switch (this.state.activeView) {
            case 'dashboard':
                this.renderDashboard();
                break;
            case 'subjects':
                this.renderSubjects();
                break;
            case 'schedule':
                this.renderSchedule();
                break;
            case 'prerequisites':
                this.renderPrerequisites();
                break;
            case 'progress':
                this.renderProgress();
                break;
            case 'exams':
                this.renderExams();
                break;
        }
    },

    // -------------------------------------------------------------------------
    // VIEW 1: DASHBOARD
    // -------------------------------------------------------------------------

    renderDashboard: function () {
        // Calculate Metrics
        const totalHours = this.state.topics.reduce((acc, t) => acc + (t.estimated_hours || 0), 0);
        const remainingHours = this.state.topics.reduce((acc, t) => acc + (t.remaining_hours || 0), 0);
        const completedHours = Math.max(0, totalHours - remainingHours);
        const pendingTopics = this.state.topics.filter(t => !t.completed && t.remaining_hours > 0).length;
        const completionPct = totalHours > 0 ? Math.round((completedHours / totalHours) * 100) : 0;

        document.getElementById('stat-total-hours').textContent = `${totalHours.toFixed(1)} hrs`;
        document.getElementById('stat-completed-hours').textContent = `${completedHours.toFixed(1)} hrs`;
        document.getElementById('stat-pending-topics').textContent = pendingTopics;
        document.getElementById('stat-completion-pct').textContent = `${completionPct}%`;

        // Render Today's Sessions
        const todayStr = new Date().toISOString().split('T')[0];
        document.getElementById('today-date-badge').textContent = todayStr;

        const todaySessions = this.state.sessions.filter(s => s.date === todayStr);
        const sessionsListEl = document.getElementById('dashboard-sessions-list');

        if (todaySessions.length === 0) {
            sessionsListEl.innerHTML = `
                <div class="empty-state">
                    <p>No study sessions generated for today yet.</p>
                    <button class="btn btn-sm btn-primary" onclick="app.switchView('schedule')">Generate Plan</button>
                </div>
            `;
        } else {
            sessionsListEl.innerHTML = todaySessions.map(s => `
                <div class="session-card">
                    <div class="session-time">
                        <span class="time-range">${s.start_time} - ${s.end_time}</span>
                        <span class="duration">${s.duration_hours} hrs</span>
                    </div>
                    <div class="session-details">
                        <h4>${this.escapeHtml(s.topic_name)}</h4>
                        <p>${this.escapeHtml(s.subject_name)}</p>
                    </div>
                    <div class="session-score">
                        <span class="badge badge-info">Priority ${s.priority_score.toFixed(0)}</span>
                    </div>
                </div>
            `).join('');
        }

        // Render Upcoming Exams
        const examsListEl = document.getElementById('dashboard-exams-list');
        if (this.state.exams.length === 0) {
            examsListEl.innerHTML = `<div class="empty-state"><p>No upcoming exams configured.</p></div>`;
        } else {
            examsListEl.innerHTML = this.state.exams.map(e => `
                <div class="session-card">
                    <div>
                        <h4>${this.escapeHtml(e.subject_name)}</h4>
                        <p>Exam Date: <strong>${e.exam_date}</strong></p>
                    </div>
                    <div>
                        <span class="badge badge-warning">Upcoming</span>
                    </div>
                </div>
            `).join('');
        }
    },

    // -------------------------------------------------------------------------
    // VIEW 2: SUBJECTS & TOPICS
    // -------------------------------------------------------------------------

    renderSubjects: function () {
        const container = document.getElementById('subjects-container');
        if (this.state.subjects.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No subjects added yet. Click "+ Add Subject" to get started.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.state.subjects.map(subj => {
            const subjTopics = this.state.topics.filter(t => t.subject_id === subj.id);
            return `
                <div class="subject-card">
                    <div class="subject-header">
                        <div class="subject-title">
                            <h3>📚 ${this.escapeHtml(subj.name)}</h3>
                            <span class="badge badge-secondary">${subjTopics.length} Topics</span>
                        </div>
                        <button class="btn btn-sm btn-danger" onclick="app.handleDeleteSubject(${subj.id})">Delete Subject</button>
                    </div>

                    <div class="topics-grid">
                        ${subjTopics.length === 0 ? '<p class="text-muted">No topics added under this subject.</p>' : subjTopics.map(t => `
                            <div class="topic-card">
                                <div class="topic-header">
                                    <h4>${this.escapeHtml(t.name)}</h4>
                                    <button class="btn btn-sm btn-danger" onclick="app.handleDeleteTopic(${t.id})">✕</button>
                                </div>
                                <div class="topic-meta">
                                    <span class="badge badge-info">Diff ${t.difficulty}/5</span>
                                    <span class="badge badge-warning">Imp ${t.importance}/5</span>
                                    <span class="badge badge-secondary">${t.remaining_hours} / ${t.estimated_hours} hrs</span>
                                    ${t.completed ? '<span class="badge badge-success">Completed</span>' : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }).join('');
    },

    filterTopics: function () {
        const query = document.getElementById('topic-search-input').value.toLowerCase();
        const cards = document.querySelectorAll('.subject-card');
        cards.forEach(card => {
            const text = card.textContent.toLowerCase();
            card.style.display = text.includes(query) ? 'block' : 'none';
        });
    },

    // -------------------------------------------------------------------------
    // VIEW 3: SCHEDULE GENERATOR
    // -------------------------------------------------------------------------

    renderSchedule: function () {
        if (this.state.lastScheduleResult) {
            this.displayScheduleResults(this.state.lastScheduleResult);
        }
    },

    handleGenerateSchedule: async function (e) {
        e.preventDefault();
        const hours = parseFloat(document.getElementById('sched-hours').value);
        const dateStr = document.getElementById('sched-date').value;
        const duration = parseFloat(document.getElementById('sched-duration').value);
        const start = document.getElementById('sched-start').value;

        const btn = document.getElementById('btn-submit-generate');
        btn.disabled = true;
        btn.innerHTML = `<span class="icon">⏳</span> Running Max Heap Scheduler...`;

        try {
            const result = await this.apiFetch('/api/schedule/generate', 'POST', {
                daily_available_hours: hours,
                target_date: dateStr,
                max_session_duration: duration,
                start_time: start
            });

            this.state.lastScheduleResult = result;
            this.displayScheduleResults(result);
            this.showToast("Study schedule generated successfully!", "success");

            // Refresh sessions list
            this.state.sessions = await this.apiFetch('/api/sessions');
        } catch (err) {
            console.error("Schedule generation error:", err);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<span class="icon">🚀</span> Generate Optimized Schedule`;
        }
    },

    displayScheduleResults: function (result) {
        const metaEl = document.getElementById('schedule-meta-badges');
        const timelineEl = document.getElementById('schedule-sessions-timeline');

        metaEl.innerHTML = `
            <span class="badge badge-success">${result.total_hours_scheduled} hrs Allocated</span>
            <span class="badge badge-info">${result.remaining_day_hours} hrs Free</span>
            ${result.has_cycle ? '<span class="badge badge-danger">Circular Dependency Detected</span>' : '<span class="badge badge-secondary">Graph DAG Valid</span>'}
        `;

        if (!result.sessions || result.sessions.length === 0) {
            timelineEl.innerHTML = `
                <div class="empty-state">
                    <p>No study sessions could be scheduled. All topics may be completed or blocked by incomplete prerequisites.</p>
                </div>
            `;
            return;
        }

        timelineEl.innerHTML = result.sessions.map(s => `
            <div class="session-card">
                <div class="session-time">
                    <span class="time-range">${s.start_time} - ${s.end_time}</span>
                    <span class="duration">${s.duration_hours} hrs</span>
                </div>
                <div class="session-details">
                    <h4>${this.escapeHtml(s.topic_name)}</h4>
                    <p>${this.escapeHtml(s.subject_name)}</p>
                </div>
                <div class="session-score">
                    <span class="badge badge-info">Priority Score: ${s.priority_score.toFixed(1)}</span>
                </div>
            </div>
        `).join('');
    },

    // -------------------------------------------------------------------------
    // VIEW 4: PREREQUISITES VISUALIZATION
    // -------------------------------------------------------------------------

    renderPrerequisites: function () {
        const topoEl = document.getElementById('topo-order-display');
        const listEl = document.getElementById('prerequisites-list-container');
        const alertEl = document.getElementById('cycle-alert-container');

        // Extract topic names for display
        const topicMap = {};
        this.state.topics.forEach(t => { topicMap[t.id] = t.name; });

        if (this.state.topics.length === 0) {
            topoEl.innerHTML = `<span class="chip">No topics added yet</span>`;
            listEl.innerHTML = `<div class="empty-state"><p>No topic prerequisites configured.</p></div>`;
            return;
        }

        // Display topics and their prerequisite locks
        listEl.innerHTML = this.state.topics.map(t => {
            const hasPrereqs = t.prerequisites && t.prerequisites.length > 0;
            const prereqNames = hasPrereqs ? t.prerequisites.map(id => topicMap[id] || `Topic #${id}`) : [];

            // Check if prerequisites are satisfied
            const allSatisfied = hasPrereqs ? t.prerequisites.every(id => {
                const target = this.state.topics.find(top => top.id === id);
                return target && target.completed;
            }) : true;

            return `
                <div class="session-card">
                    <div>
                        <h4>${this.escapeHtml(t.name)}</h4>
                        <p>Subject: <strong>${this.escapeHtml(t.subject_name)}</strong></p>
                        ${hasPrereqs ? `<p class="text-muted">Requires: ${prereqNames.map(n => `<strong>${this.escapeHtml(n)}</strong>`).join(', ')}</p>` : '<p class="text-muted">No prerequisites required.</p>'}
                    </div>
                    <div>
                        ${t.completed ? '<span class="badge badge-success">Completed</span>' : (allSatisfied ? '<span class="badge badge-info">Prerequisites Met (Unlocked)</span>' : '<span class="badge badge-warning">Prerequisites Incomplete (Locked)</span>')}
                    </div>
                </div>
            `;
        }).join('');
    },

    // -------------------------------------------------------------------------
    // VIEW 5: PROGRESS TRACKING
    // -------------------------------------------------------------------------

    renderProgress: function () {
        const totalHours = this.state.topics.reduce((acc, t) => acc + (t.estimated_hours || 0), 0);
        const remainingHours = this.state.topics.reduce((acc, t) => acc + (t.remaining_hours || 0), 0);
        const completedHours = Math.max(0, totalHours - remainingHours);
        const completionPct = totalHours > 0 ? Math.round((completedHours / totalHours) * 100) : 0;

        document.getElementById('overall-progress-fill').style.width = `${completionPct}%`;
        document.getElementById('overall-progress-text').textContent = `${completionPct}% Complete (${completedHours.toFixed(1)} / ${totalHours.toFixed(1)} hrs)`;

        const tbody = document.getElementById('progress-table-body');
        if (this.state.topics.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center">No topics available.</td></tr>`;
            return;
        }

        tbody.innerHTML = this.state.topics.map(t => `
            <tr>
                <td><strong>${this.escapeHtml(t.subject_name)}</strong></td>
                <td>${this.escapeHtml(t.name)}</td>
                <td><span class="badge badge-info">${t.difficulty}/5</span></td>
                <td><span class="badge badge-warning">${t.importance}/5</span></td>
                <td>${t.estimated_hours} hrs</td>
                <td>
                    <input type="number" min="0" max="${t.estimated_hours}" step="0.5" value="${t.remaining_hours}" style="width: 70px;" onchange="app.handleUpdateProgress(${t.id}, this.value, ${t.completed})"> hrs
                </td>
                <td>${t.completed ? '<span class="badge badge-success">Completed</span>' : '<span class="badge badge-secondary">Pending</span>'}</td>
                <td>
                    <button class="btn btn-sm ${t.completed ? 'btn-secondary' : 'btn-primary'}" onclick="app.handleUpdateProgress(${t.id}, ${t.completed ? t.estimated_hours : 0}, ${!t.completed})">
                        ${t.completed ? 'Mark Pending' : 'Mark Complete'}
                    </button>
                </td>
            </tr>
        `).join('');
    },

    handleUpdateProgress: async function (topicId, remainingHours, completed) {
        try {
            await this.apiFetch(`/api/topics/${topicId}/progress`, 'PATCH', {
                remaining_hours: parseFloat(remainingHours),
                completed: Boolean(completed)
            });
            this.showToast("Topic progress updated!", "success");
            this.refreshAllData();
        } catch (err) {
            console.error("Failed to update topic progress:", err);
        }
    },

    // -------------------------------------------------------------------------
    // VIEW 6: EXAMS
    // -------------------------------------------------------------------------

    renderExams: function () {
        const container = document.getElementById('exams-container');
        if (this.state.exams.length === 0) {
            container.innerHTML = `<div class="empty-state"><p>No upcoming exams added. Click "+ Add Exam Date".</p></div>`;
            return;
        }

        container.innerHTML = this.state.exams.map(e => `
            <div class="card">
                <h3>📝 ${this.escapeHtml(e.subject_name)}</h3>
                <p style="margin: 12px 0;">Exam Date: <strong>${e.exam_date}</strong></p>
                <span class="badge badge-warning">High Urgency Priority Factor</span>
            </div>
        `).join('');
    },

    // -------------------------------------------------------------------------
    // MODAL & FORM HANDLERS
    // -------------------------------------------------------------------------

    openModal: function (modalId) {
        document.getElementById(modalId).classList.add('active');
    },

    closeModal: function (modalId) {
        document.getElementById(modalId).classList.remove('active');
    },

    populateModalSelects: function () {
        // Populate Subject Selects
        const subjectSelects = [document.getElementById('topic-subject'), document.getElementById('exam-subject')];
        subjectSelects.forEach(select => {
            if (select) {
                select.innerHTML = '<option value="">-- Select Subject --</option>' +
                    this.state.subjects.map(s => `<option value="${s.id}">${this.escapeHtml(s.name)}</option>`).join('');
            }
        });

        // Populate Prerequisite Select
        const prereqSelect = document.getElementById('topic-prereqs');
        if (prereqSelect) {
            prereqSelect.innerHTML = this.state.topics.map(t => `<option value="${t.id}">${this.escapeHtml(t.subject_name)} → ${this.escapeHtml(t.name)}</option>`).join('');
        }
    },

    handleCreateSubject: async function (e) {
        e.preventDefault();
        const name = document.getElementById('subj-name').value;
        try {
            await this.apiFetch('/api/subjects', 'POST', { name });
            this.showToast("Subject added successfully!", "success");
            this.closeModal('modal-subject');
            document.getElementById('subj-name').value = '';
            this.refreshAllData();
        } catch (err) {
            console.error(err);
        }
    },

    handleDeleteSubject: async function (subjectId) {
        if (!confirm("Are you sure you want to delete this subject and all its topics?")) return;
        try {
            await this.apiFetch(`/api/subjects/${subjectId}`, 'DELETE');
            this.showToast("Subject deleted.", "success");
            this.refreshAllData();
        } catch (err) {
            console.error(err);
        }
    },

    handleCreateTopic: async function (e) {
        e.preventDefault();
        const subjectId = parseInt(document.getElementById('topic-subject').value);
        const name = document.getElementById('topic-name').value;
        const difficulty = parseInt(document.getElementById('topic-difficulty').value);
        const importance = parseInt(document.getElementById('topic-importance').value);
        const hours = parseFloat(document.getElementById('topic-hours').value);
        const examDate = document.getElementById('topic-exam-date').value || null;

        const prereqsSelect = document.getElementById('topic-prereqs');
        const prerequisites = Array.from(prereqsSelect.selectedOptions).map(opt => parseInt(opt.value));

        try {
            await this.apiFetch('/api/topics', 'POST', {
                subject_id: subjectId,
                name: name,
                difficulty: difficulty,
                importance: importance,
                estimated_hours: hours,
                exam_date: examDate,
                prerequisites: prerequisites
            });

            this.showToast("Topic added successfully!", "success");
            this.closeModal('modal-topic');
            document.getElementById('topic-name').value = '';
            this.refreshAllData();
        } catch (err) {
            console.error(err);
        }
    },

    handleDeleteTopic: async function (topicId) {
        if (!confirm("Delete this topic?")) return;
        try {
            await this.apiFetch(`/api/topics/${topicId}`, 'DELETE');
            this.showToast("Topic deleted.", "success");
            this.refreshAllData();
        } catch (err) {
            console.error(err);
        }
    },

    handleCreateExam: async function (e) {
        e.preventDefault();
        const subjectId = parseInt(document.getElementById('exam-subject').value);
        const examDate = document.getElementById('exam-date').value;

        try {
            await this.apiFetch('/api/exams', 'POST', {
                subject_id: subjectId,
                exam_date: examDate
            });

            this.showToast("Exam date added!", "success");
            this.closeModal('modal-exam');
            this.refreshAllData();
        } catch (err) {
            console.error(err);
        }
    },

    // -------------------------------------------------------------------------
    // UTILITY HELPERS
    // -------------------------------------------------------------------------

    showToast: function (message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `<span>${type === 'success' ? '✅' : '⚠️'}</span> ${this.escapeHtml(message)}`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3500);
    },

    escapeHtml: function (str) {
        if (!str) return '';
        return String(str).replace(/[&<>"']/g, function (m) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            }[m];
        });
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
