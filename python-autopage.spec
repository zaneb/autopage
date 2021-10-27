%global srcname autopage

# Macros for pyproject (Fedora) vs. setup.py (CentOS)
%if 0%{?fedora} >= 33
%bcond_without pyproject
%else
%bcond_with pyproject
%endif

# Macros for disabling tests on CentOS 7
%if 0%{?el7}
%bcond_with enable_tests
%else
%bcond_without enable_tests
%endif


Name:           python-%{srcname}
Version:        0.4.0
Release:        2%{?dist}
Summary:        A Python library to provide automatic paging for console output
License:        ASL 2.0
URL:            https://pypi.python.org/pypi/autopage
Source0:        %{pypi_source}
Source1:        setup.py

BuildArch:      noarch

%global _description %{expand:
Autopage is a Python library to provide automatic paging for console output.}


%description %_description

%package -n python3-%{srcname}
Summary:        %{summary}
BuildRequires:  python3-devel
%if %{with pyproject}
BuildRequires:  pyproject-rpm-macros
%else
%if %{with enable_tests}
BuildRequires:  %{py3_dist fixtures}
%endif
%endif

%description -n python3-%{srcname} %_description

%prep
%autosetup -n %{srcname}-%{version}

%if %{with pyproject}
%generate_buildrequires
%pyproject_buildrequires -e pep8,%{toxenv}
%else
cp %{SOURCE1} ./
%endif

%build
%if %{with pyproject}
%pyproject_wheel
%else
%py3_build
%endif

%install
%if %{with pyproject}
%pyproject_install
%pyproject_save_files autopage
%else
%py3_install
%endif

%check
%if %{with enable_tests}
%if %{with pyproject}
%tox
%else
%{python3} setup.py test
%endif
%endif

%if %{with pyproject}
%files -n python3-%{srcname} -f %{pyproject_files}
%else
%files -n python3-%{srcname}
%{python3_sitelib}/%{srcname}-*.egg-info/
%{python3_sitelib}/%{srcname}/
%endif
%license LICENSE
%doc README.md

%changelog
* Wed Oct 27 2021 Zane Bitter <zaneb@fedoraproject.org> 0.4.0-2
- Update specfile to build for more distros

* Mon Jul 12 2021 Zane Bitter <zaneb@fedoraproject.org> 0.4.0-1
- Update to v0.4.0

* Fri Jun 25 2021 Zane Bitter <zaneb@fedoraproject.org> 0.3.1-1
- Update to v0.3.1 for easier packaging

* Fri Jun 25 2021 Zane Bitter <zaneb@fedoraproject.org> 0.3.0-2
- Support building for EPEL

* Fri Jun 18 2021 Zane Bitter <zaneb@fedoraproject.org> 0.3.0-1
- Initial build
