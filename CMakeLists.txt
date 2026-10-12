if(CONFIG_ZMK_HIRES_DIAL)
  # The pinned dial module uses ZMK behavior headers without exporting this path.
  zephyr_include_directories(${APPLICATION_SOURCE_DIR}/include)
  # Adapt the upstream dial API name to the pinned cormoran ZMK endpoint API.
  zephyr_compile_definitions(zmk_endpoints_selected=zmk_endpoint_get_selected)
endif()

if(CONFIG_EQUINOX_PAT_DIAGNOSTICS)
  zephyr_library()
  zephyr_library_sources(src/pat_diagnostics.c)
  if(CONFIG_EQUINOX_CRASH_DIAGNOSTICS)
    zephyr_library_include_directories(${APPLICATION_SOURCE_DIR}/include)
    zephyr_library_sources(src/central_crash_diagnostics.c)
    zephyr_link_libraries(-Wl,--wrap=zmk_watchdog_pending_set)
  endif()
endif()
if(CONFIG_EQUINOX_PMW_DIAGNOSTICS)
  zephyr_library()
  zephyr_library_include_directories(${APPLICATION_SOURCE_DIR}/include)
  zephyr_library_sources(src/pmw_diagnostics.c)
endif()

# Keep cormoran Studio RPC and the shared west checkout unchanged. Substitute
# only the pinned driver's compilation unit in this keyboard's build tree.
if(CONFIG_PMW3610)
  get_target_property(equinox_app_sources app SOURCES)
  set(equinox_pmw_found FALSE)
  foreach(source IN LISTS equinox_app_sources)
    if(source MATCHES "zmk-driver-pmw3610-with-custom-studio-rpc/src/pmw3610.c$")
      set(equinox_pmw_found TRUE)
      set(patched_pmw "${CMAKE_CURRENT_BINARY_DIR}/equinox_pmw3610.c")
      execute_process(
        COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/patch_pmw_guard.py
                ${source} ${patched_pmw}
        RESULT_VARIABLE patch_result)
      if(NOT patch_result EQUAL 0)
        message(FATAL_ERROR "Equinox PMW guard could not be applied")
      endif()
      get_filename_component(pmw_src_dir ${source} DIRECTORY)
      target_include_directories(app PRIVATE ${pmw_src_dir})
      list(REMOVE_ITEM equinox_app_sources ${source})
      list(APPEND equinox_app_sources ${patched_pmw})
      set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
                   ${source} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/patch_pmw_guard.py)
    endif()
  endforeach()
  if(NOT equinox_pmw_found)
    message(FATAL_ERROR "Equinox PMW source not found; refusing an unguarded build")
  endif()
  set_property(TARGET app PROPERTY SOURCES ${equinox_app_sources})
endif()
