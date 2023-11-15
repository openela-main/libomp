%global maj_ver 16
%global libomp_version %{maj_ver}.0.6
#global rc_ver 4
%global libomp_srcdir openmp-%{libomp_version}%{?rc_ver:rc%{rc_ver}}.src
%global cmake_srcdir cmake-%{libomp_version}%{?rc_ver:rc%{rc_ver}}.src


%ifarch ppc64le
%global libomp_arch ppc64
%else
%global libomp_arch %{_arch}
%endif

%ifarch %{ix86}
%bcond_with testpkg
%else
%bcond_without testpkg
%endif

Name: libomp
Version: %{libomp_version}%{?rc_ver:~rc%{rc_ver}}
Release: 3%{?dist}
Summary: OpenMP runtime for clang

License: NCSA
URL: http://openmp.llvm.org
Source0: https://github.com/llvm/llvm-project/releases/download/llvmorg-%{libomp_version}%{?rc_ver:-rc%{rc_ver}}/%{libomp_srcdir}.tar.xz
Source1: https://github.com/llvm/llvm-project/releases/download/llvmorg-%{libomp_version}%{?rc_ver:-rc%{rc_ver}}/%{libomp_srcdir}.tar.xz.sig
Source2: release-keys.asc
Source3: run-lit-tests
Source4: lit.fedora.cfg.py
Source5:	https://github.com/llvm/llvm-project/releases/download/llvmorg-%{libomp_version}%{?rc_ver:-rc%{rc_ver}}/%{cmake_srcdir}.tar.xz
Source6:	https://github.com/llvm/llvm-project/releases/download/llvmorg-%{libomp_version}%{?rc_ver:-rc%{rc_ver}}/%{cmake_srcdir}.tar.xz.sig

BuildRequires: clang
# For clang-offload-packager
BuildRequires: clang-tools-extra
BuildRequires: cmake
BuildRequires: ninja-build
BuildRequires: elfutils-libelf-devel
BuildRequires: perl
BuildRequires: perl-Data-Dumper
BuildRequires: perl-Encode
BuildRequires: libffi-devel
# RHEL specific: libomp requires libterminfo
BuildRequires: ncurses-devel

# For gpg source verification
BuildRequires:	gnupg2


# libomptarget needs the llvm cmake files
BuildRequires: llvm-devel

Requires: elfutils-libelf%{?isa}

# libomp does not support s390x.
ExcludeArch: s390x

%description
OpenMP runtime for clang.

%package devel
Summary: OpenMP header files
Requires: %{name}%{?isa} = %{version}-%{release}
Requires: clang-resource-filesystem%{?isa} = %{version}

%description devel
OpenMP header files.

%if %{with testpkg}

%package test
Summary: OpenMP regression tests
Requires: %{name}%{?isa} = %{version}-%{release}
Requires: %{name}-devel%{?isa} = %{version}-%{release}
Requires: clang
Requires: llvm
Requires: gcc
Requires: gcc-c++
Requires: python3-lit

%description test
OpenMP regression tests

%endif

%prep
%{gpgverify} --keyring='%{SOURCE2}' --signature='%{SOURCE1}' --data='%{SOURCE0}'
%{gpgverify} --keyring='%{SOURCE2}' --signature='%{SOURCE6}' --data='%{SOURCE5}'
%setup -T -q -b 5 -n %{cmake_srcdir}
# TODO: It would be more elegant to set -DLLVM_COMMON_CMAKE_UTILS=%{_builddir}/%{cmake_srcdir},
# but this is not a CACHED variable, so we can't actually set it externally :(
cd ..
mv %{cmake_srcdir} cmake
%autosetup -n %{libomp_srcdir} -p2

%build
# LTO causes build failures in this package.  Disable LTO for now
# https://bugzilla.redhat.com/show_bug.cgi?id=1988155
%define _lto_cflags %{nil}

mkdir -p %{_vpath_builddir}
cd %{_vpath_builddir}

%cmake ..  -GNinja \
	-DLIBOMP_INSTALL_ALIASES=OFF \
	-DCMAKE_MODULE_PATH=%{_libdir}/cmake/llvm \
	-DLLVM_DIR=%{_libdir}/cmake/llvm \
	-DCMAKE_INSTALL_INCLUDEDIR=%{_libdir}/clang/%{maj_ver}/include \
%if 0%{?__isa_bits} == 64
	-DOPENMP_LIBDIR_SUFFIX=64 \
%else
	-DOPENMP_LIBDIR_SUFFIX= \
%endif
	-DCMAKE_SKIP_RPATH:BOOL=ON

%cmake_build


%install
cd %{_vpath_builddir}
%cmake_install

%if %{with testpkg}
# Test package setup
%global libomp_srcdir %{_datadir}/libomp/src/
%global libomp_testdir %{libomp_srcdir}/runtime/test/
%global lit_cfg %{libomp_testdir}/%{_arch}.site.cfg.py
%global lit_fedora_cfg %{_datadir}/libomp/lit.fedora.cfg.py

# Install test files
cd ..
install -d %{buildroot}%{libomp_srcdir}/runtime
cp -R runtime/test  %{buildroot}%{libomp_srcdir}/runtime
cp -R runtime/src  %{buildroot}%{libomp_srcdir}/runtime

cd %{_vpath_builddir}
# Generate lit config files.  Strip off the last line that initiates the
# test run, so we can customize the configuration.
head -n -1 runtime/test/lit.site.cfg >> %{buildroot}%{lit_cfg}

# Install custom fedora config file
cp %{SOURCE4} %{buildroot}%{lit_fedora_cfg}

# Patch lit config files to load custom fedora config
echo "lit_config.load_config(config, '%{lit_fedora_cfg}')" >> %{buildroot}%{lit_cfg}

# Install test script
install -d %{buildroot}%{_libexecdir}/tests/libomp
install -m 0755 %{SOURCE3} %{buildroot}%{_libexecdir}/tests/libomp


%endif

# Remove static libraries with equivalent shared libraries
rm -rf %{buildroot}%{_libdir}/libarcher_static.a

%check
cd %{_vpath_builddir}
%cmake_build --target check-openmp || true

%files
%license LICENSE.TXT
%{_libdir}/libomp.so
%{_libdir}/libompd.so
%ifnarch %{arm}
%{_libdir}/libarcher.so
%endif
%ifnarch %{ix86} %{arm}
# libomptarget is not supported on 32-bit systems.
%{_libdir}/libomptarget.rtl.amdgpu.so.%{maj_ver}
%{_libdir}/libomptarget.rtl.amdgpu.nextgen.so.%{maj_ver}
%{_libdir}/libomptarget.rtl.cuda.so.%{maj_ver}
%{_libdir}/libomptarget.rtl.cuda.nextgen.so.%{maj_ver}
%{_libdir}/libomptarget.rtl.%{libomp_arch}.so.%{maj_ver}
%{_libdir}/libomptarget.rtl.%{libomp_arch}.nextgen.so.%{maj_ver}
%{_libdir}/libomptarget.so.%{maj_ver}
%endif

%files devel
%{_libdir}/clang/%{maj_ver}/include/omp.h
%{_libdir}/cmake/openmp/FindOpenMPTarget.cmake
%ifnarch %{arm}
%{_libdir}/clang/%{maj_ver}/include/omp-tools.h
%{_libdir}/clang/%{maj_ver}/include/ompt.h
%{_libdir}/clang/%{maj_ver}/include/ompt-multiplex.h
%endif
%ifnarch %{ix86} %{arm}
# libomptarget is not supported on 32-bit systems.
%{_libdir}/libomptarget.rtl.amdgpu.so
%{_libdir}/libomptarget.rtl.amdgpu.nextgen.so
%{_libdir}/libomptarget.rtl.cuda.so
%{_libdir}/libomptarget.rtl.cuda.nextgen.so
%{_libdir}/libomptarget.rtl.%{libomp_arch}.so
%{_libdir}/libomptarget.rtl.%{libomp_arch}.nextgen.so
%{_libdir}/libomptarget.devicertl.a
%{_libdir}/libomptarget-amdgpu-*.bc
%{_libdir}/libomptarget-nvptx-*.bc
%{_libdir}/libomptarget.so
%endif

%if %{with testpkg}
%files test
%{_datadir}/libomp
%{_libexecdir}/tests/libomp/
%endif

%changelog
* Sat Jul 15 2023 Tom Stellard <tstellar@redhat.com> - 16.0.6-3
- Remove duplicated installed binaries

* Wed Jul 05 2023 Tom Stellard <tstellar@redhat.com> - 16.0.6-2
- Add explict libomp requres to libomp-devel

* Fri Jun 23 2023 Tom Stellard <tstellar@redhat.com> - 16.0.6-1
- 16.0.6 Release

* Fri Apr 28 2023 Tom Stellard <tstellar@redhat.com> - 16.0.0-1
- Release 16.0.0

* Thu Jan 19 2023 Tom Stellard <tstellar@redhat.com> - 15.0.7-1
- Update to LLVM 15.0.7

* Tue Sep 06 2022 Nikita Popov <npopov@redhat.com> - 15.0.0-1
- Update to LLVM 15.0.0

* Wed Aug 10 2022 Tom Stellard <tstellar@redhat.com> - 14.0.6-2
- Drop -test sub-package on i686

* Tue Jun 28 2022 Tom Stellard <tstellar@redhat.com> - 14.0.6-1
- 14.0.6 Release

* Wed May 18 2022 Timm Bäder <tbaeder@redhat.com> - 14.00-2
- Backport 40d3a0ba4d9e5452c0a68cfdaa8e88eb8ed5c63d to
  fix a strict aliasing issue.

* Thu Apr 07 2022 Timm Bäder <tbaeder@redhat.com> - 14.0.0-1
- Update to 14.0.0

* Thu Feb 03 2022 Tom Stellard <tstellar@redhat.com> - 13.0.1-1
- 13.0.1 Release

* Fri Oct 15 2021 Tom Stellard <tstellar@redhat.com> - 13.0.0-1
- 13.0.0 Release

* Fri Jul 16 2021 sguelton@redhat.com - 12.0.1-1
- 12.0.1 release

* Thu May 6 2021 sguelton@redhat.com - 12.0.0-1
- 12.0.0 release

* Thu Oct 29 2020 sguelton@redhat.com - 11.0.0-1
- 11.0.0 final release

* Mon Sep 21 2020 sguelton@redhat.com - 11.0.0-0.1.rc2
- 11.0.0-rc2 Release

* Fri Jul 24 2020 sguelton@redhat.com - 10.0.1-1
- 10.0.1 final

* Mon Jun 15 2020 sguelton@redhat.com - 10.0.0-2
- Better dependency specification, see rhbz#1841180

* Thu Apr 9 2020 sguelton@redhat.com - 10.0.0-1
- 10.0.0 final

* Thu Dec 19 2019 Tom Stellard <tstellar@redhat.com> - 9.0.1-1
- 9.0.1 Release

* Fri Sep 27 2019 Tom Stellard <tstellar@redhat.com> - 9.0.0-1
- 9.0.0 Release

* Thu Aug 1 2019 sguelton@redhat.com - 8.0.1-1
- 8.0.1 release

* Thu Jun 13 2019 sguelton@redhat.com - 8.0.1-0.1.rc2
- 8.0.1rc2 Release

* Mon Apr 29 2019 sguelton@redhat.com - 8.0.0-1
- 8.0.0 Release

* Fri Dec 14 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-1
- 7.0.1 Release

* Wed Dec 12 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-0.2.rc3
- Fix test failures on single-core systems

* Mon Dec 10 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-0.1.rc3
- 7.0.1-rc3 Release

* Tue Nov 27 2018 Tom Stellard <tstellar@redhat.com> - 7.0.0-1
- 7.0.0 Release

* Sat Nov 10 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-3
- Don't build libomp-test on i686

* Mon Oct 01 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-2
- Drop scl macros

* Wed Jul 11 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-1
- 6.0.1 Release

* Mon Jan 15 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-2
- Drop ExcludeArch: ppc64

* Thu Dec 21 2017 Tom Stellard <tstellar@redhat.com> - 5.0.1-1
- 5.0.1 Release.

* Wed Jun 21 2017 Tom Stellard <tstellar@redhat.com> - 4.0.1-1
- 4.0.1 Release.

* Wed Jun 07 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-3
- Rename libopenmp->libomp

* Fri May 26 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-2
- Disable build on s390x

* Mon May 15 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-1
- Initial version.
