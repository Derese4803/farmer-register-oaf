Missing Submit Button

This form has no submit button, which means that user interactions will never be sent to your Streamlit app.

To create a submit button, use the st.form_submit_button() function.

For more information, refer to the documentation for forms.

streamlit.errors.StreamlitDuplicateElementId: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).

Traceback:
File "/mount/src/farmer-register-oaf/app.py", line 110, in <module>
    if __name__ == "__main__": main()
                               ~~~~^^
File "/mount/src/farmer-register-oaf/app.py", line 107, in main
    elif pg == "Register": register_page()
                           ~~~~~~~~~~~~~^^
File "/mount/src/farmer-register-oaf/app.py", line 62, in register_page
    sel_kebele = k_col1.selectbox("Select Existing", ["None / አዲስ ጻፍ"] + kebeles)
                 ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/metrics_util.py", line 531, in wrapped_func
    result = non_optional_func(*args, **kwargs)
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/elements/widgets/selectbox.py", line 470, in selectbox
    return self._selectbox(
           ~~~~~~~~~~~~~~~^
        label=label,
        ^^^^^^^^^^^^
    ...<13 lines>...
        ctx=ctx,
        ^^^^^^^^
    )
    ^
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/elements/widgets/selectbox.py", line 542, in _selectbox
    element_id = compute_and_register_element_id(
        "selectbox",
    ...<14 lines>...
        width=width,
    )
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/elements/lib/utils.py", line 265, in compute_and_register_element_id
    _register_element_id(ctx, element_type, element_id)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/elements/lib/utils.py", line 150, in _register_element_id
    raise StreamlitDuplicateElementId(element_type)
