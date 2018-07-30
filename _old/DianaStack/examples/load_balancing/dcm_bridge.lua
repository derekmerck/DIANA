function OnStoredInstance(instanceId, tags, metadata)
    SendToPeer( instanceId, 'rest-head' )
    Delete(instanceId)
end