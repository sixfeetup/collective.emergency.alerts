from plone import api


def remove_resources_from_old_registries(content):
    """
    Let's remove these from the old css/js registries
    """
    css_resource1 = "++resource++collective.emergency.alerts/eas.css"
    css_resource2 = "++resource++collective.emergency.alerts/eas.live.css"
    js_resource = "eas.js"

    css_tool = api.portal.get_tool("portal_css")
    js_tool = api.portal.get_tool("portal_javascripts")

    css_tool.unregisterResource(css_resource1)
    css_tool.unregisterResource(css_resource2)
    js_tool.unregisterResource(js_resource)
