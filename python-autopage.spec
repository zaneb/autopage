%global srcname autopage

Name:           python-%{srcname}
Version:        0.3.0
Release:        1%{?dist}
Summary:        A Python library to provide automatic paging for console output
License:        ASL 2.0
URL:            https://pypi.python.org/pypi/autopage
Source0:        %{pypi_source}
Source1:        https://raw.githubusercontent.com/zaneb/%{srcname}/v%{version}/tox.ini

BuildArch:      noarch

%global _description %{expand:
Autopage is a Python library to provide automatic paging for console output.}


%description %_description

%package -n python3-%{srcname}
Summary:        %{summary}
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

%description -n python3-%{srcname} %_description

%prep
%autosetup -n %{srcname}-%{version}
cp %{SOURCE1} ./

%generate_buildrequires
%pyproject_buildrequires -e pep8,%{toxenv}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files autopage

%check
%tox

%files -n python3-%{srcname} -f %{pyproject_files}
%license LICENSE
%doc README.md

%changelog

* Fri Jun 18 2021 Zane Bitter <zaneb@fedoraproject.org> 0.3.0-1
- Initial build
