## 🏫 UniMIS – University Management Information System Portal

UniMIS is a modern, data-driven MIS platform designed for universities and higher-education institutions.  
It centralizes the management of **Students**, **Staff**, **Programs**, and **Infrastructure** using a clean dashboard, dynamic filters, and interactive analytics.

Built with **Django**, **Bootstrap 5**, **jQuery**, and **DataTables**, the portal provides a fast, responsive, and intuitive interface for administrators.

---

### 🚀 Key Features

- **Student & Staff Records Management**  
  View and manage institution-wide datasets with server-side DataTables for high performance.

- **Program & Discipline Expansion (Accordion View)**  
  Each college row expands to reveal detailed program-wise metrics:
  - Gender distribution  
  - Category (M/F/O)  
  - Religion (M/F/O)  
  - Disability (M/F/O)  
  - Washroom infrastructure  

- **Academic Year Locking System**  
  Automatically disables edit/delete actions for records in previous academic years.  
  Uses backend-provided `CURRENT_ACADEMIC_YEAR` to enforce access control dynamically.

- **Excel Exporting**  
  Export filtered and sorted student/staff data to `.xlsx` with correct filenames and server-side processing.

- **Responsive Dashboards & UI**  
  Clean Bootstrap 5 design, custom dropdowns, and notification system for disabled actions.

- **Secure Role Handling**  
  Integrates user roles (superuser/admin/user) and prevents unauthorized edits.

---

### 🛠️ Tech Stack

- **Backend:** Django / Python  
- **Frontend:** Bootstrap 5, jQuery 3.7, DataTables 1.13  
- **Export:** DataTables Buttons, JSZip, Excel generation API  
- **Icons:** Bootstrap Icons  

---

### 📂 Features Under the Hood

- Server-side filtered DataTables with AJAX  
- Deep nested accordion templates for program metrics  
- Automatic UI locking for non-editable years  
- Custom notification system for disabled actions  
- Shared label maps for clean rendering of gender/category/religion/disability datasets  
- Clean, modular JS functions for students and staff tables  

---

### 📌 Perfect For

- Colleges and universities  
- Institutional dashboards  
- Data analytics portals  
- Education MIS platforms  
