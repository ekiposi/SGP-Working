document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const employeeForm = document.getElementById('employeeForm');
    const departmentSelect = document.getElementById('department');
    const roleSelect = document.getElementById('role');
    const employeeListBtn = document.getElementById('employeeListBtn');
    const addEmployeeBtn = document.getElementById('addEmployeeBtn');
    const registrationForm = document.getElementById('registrationForm');
    const employeeList = document.getElementById('employeeList');
    const searchInput = document.getElementById('searchInput');
    const employeeTableBody = document.getElementById('employeeTableBody');

    // Event Listeners
    departmentSelect.addEventListener('change', updateRoles);
    employeeForm.addEventListener('submit', handleEmployeeRegistration);
    employeeListBtn.addEventListener('click', showEmployeeList);
    addEmployeeBtn.addEventListener('click', showRegistrationForm);
    searchInput.addEventListener('input', filterEmployees);

    // Functions
    async function updateRoles() {
        const department = departmentSelect.value;
        if (!department) return;

        try {
            const response = await fetch(`/get_roles/${department}`);
            const roles = await response.json();
            
            roleSelect.innerHTML = '<option value="">Select Role</option>';
            roles.forEach(role => {
                const option = document.createElement('option');
                option.value = role;
                option.textContent = role;
                roleSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error fetching roles:', error);
        }
    }

    async function handleEmployeeRegistration(e) {
        e.preventDefault();

        const formData = {
            full_name: document.getElementById('fullName').value,
            department: departmentSelect.value,
            role: roleSelect.value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value,
            emergency_contact: document.getElementById('emergencyContact').value
        };

        try {
            const response = await fetch('/register_employee', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (response.ok) {
                showQRCode(data.qr_code);
                employeeForm.reset();
                alert('Employee registered successfully!');
            } else {
                alert('Error: ' + data.error);
            }
        } catch (error) {
            console.error('Error registering employee:', error);
            alert('Error registering employee. Please try again.');
        }
    }

    function showQRCode(qrCodeBase64) {
        const modal = new bootstrap.Modal(document.getElementById('qrCodeModal'));
        const qrCodeImage = document.getElementById('qrCodeImage');
        qrCodeImage.src = `data:image/png;base64,${qrCodeBase64}`;
        modal.show();

        // Download QR Code
        document.getElementById('downloadQR').onclick = function() {
            const link = document.createElement('a');
            link.download = 'employee-qr.png';
            link.href = qrCodeImage.src;
            link.click();
        };

        // Print QR Code
        document.getElementById('printQR').onclick = function() {
            const printWindow = window.open('', '', 'height=500,width=500');
            printWindow.document.write('<html><head><title>Print QR Code</title></head><body>');
            printWindow.document.write('<img src="' + qrCodeImage.src + '" style="max-width: 100%;">');
            printWindow.document.write('</body></html>');
            printWindow.document.close();
            printWindow.print();
        };
    }

    async function loadEmployees() {
        try {
            const response = await fetch('/employees');
            const employees = await response.json();
            displayEmployees(employees);
        } catch (error) {
            console.error('Error loading employees:', error);
        }
    }

    function displayEmployees(employees) {
        employeeTableBody.innerHTML = '';
        employees.forEach(employee => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${employee.full_name}</td>
                <td>${employee.department}</td>
                <td>${employee.role}</td>
                <td>${employee.email}</td>
                <td>
                    <button class="btn btn-sm btn-primary btn-action" onclick="editEmployee(${employee.id})">Edit</button>
                    <button class="btn btn-sm btn-danger btn-action" onclick="deleteEmployee(${employee.id})">Delete</button>
                </td>
            `;
            employeeTableBody.appendChild(row);
        });
    }

    function showEmployeeList() {
        registrationForm.style.display = 'none';
        employeeList.style.display = 'block';
        loadEmployees();
    }

    function showRegistrationForm() {
        employeeList.style.display = 'none';
        registrationForm.style.display = 'block';
    }

    function filterEmployees() {
        const searchTerm = searchInput.value.toLowerCase();
        const rows = employeeTableBody.getElementsByTagName('tr');

        Array.from(rows).forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    }

    // Initialize the form view
    showRegistrationForm();
});
